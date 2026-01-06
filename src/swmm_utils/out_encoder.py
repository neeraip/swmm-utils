"""SWMM output file encoder - encode SWMM output data to .json or .parquet formats."""

import json
from typing import Any, Dict, Optional, Union
from pathlib import Path


class SwmmOutputEncoder:
    """Encode SWMM output data to .json or .parquet formats."""

    def encode_to_file(
        self,
        output: "SwmmOutput",  # noqa: F821
        filepath: Union[str, Path],
        file_format: Optional[str] = None,
    ) -> None:
        """Encode SWMM output to a file.

        Args:
            output: SwmmOutput instance to export
            filepath: Output file path
            file_format: Output format ('json', 'parquet'). If None, inferred from filepath extension.
        """
        if file_format is None:
            # Infer format from file extension
            ext = Path(filepath).suffix.lower()
            format_map = {".json": "json", ".parquet": "parquet"}
            file_format = format_map.get(ext, "json")

        if file_format == "json":
            self.encode_to_json(output, filepath, pretty=True)
        elif file_format == "parquet":
            self.encode_to_parquet(output, filepath)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    def encode_to_json(
        self,
        output: "SwmmOutput",  # noqa: F821
        filepath: Union[str, Path],
        pretty: bool = True,
    ) -> None:
        """
        Export output file data to JSON format.

        Exports all data that was loaded during initialization.
        If initialized with load_time_series=False (default), exports only metadata.
        If initialized with load_time_series=True, exports metadata and all time series data.

        Args:
            output: SwmmOutput instance to export
            filepath: Path where JSON file will be saved
            pretty: Whether to pretty-print JSON (default True)
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "header": output._data["header"],
            "metadata": {
                "labels": output._data["metadata"]["labels"],
                "pollutant_units": output._data["metadata"]["pollutant_units"],
                "properties": output._data["metadata"]["properties"],
                "variables": output._data["metadata"]["variables"],
                "start_date": output._data["metadata"]["start_date"].isoformat(),
                "report_interval_seconds": output._data["metadata"][
                    "report_interval_seconds"
                ],
                "n_periods": output._data["metadata"]["n_periods"],
            },
            "summary": output.summary(),
        }

        # Add time series if it was loaded
        if output._data.get("time_series") is not None:
            output_data["time_series"] = output._data["time_series"]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                output_data,
                f,
                indent=2 if pretty else None,
                ensure_ascii=False,
            )

    def encode_to_parquet(
        self,
        output: "SwmmOutput",  # noqa: F821
        filepath: Union[str, Path, None] = None,
        single_file: bool = True,
    ) -> None:
        """
        Export output file metadata to Parquet format.

        Args:
            output: SwmmOutput instance to export
            filepath: Path where Parquet file will be saved. If single_file=False,
                     this is treated as a directory path.
            single_file: Whether to save as single file (True) or multiple files (False).
                        If False, creates separate parquet files for each data type.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for Parquet export. Install with: pip install pandas"
            ) from exc

        try:
            import pyarrow  # pylint: disable=unused-import # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "pyarrow is required for Parquet export. Install with: pip install pyarrow"
            ) from exc

        if single_file:
            # Export all metadata as a single parquet file
            if filepath is None:
                raise ValueError("filepath is required when single_file=True")
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Create a summary dataframe
            summary_data = []
            summary = output.summary()

            for key, value in summary.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                summary_data.append({"field": key, "value": str(value)})

            df = pd.DataFrame(summary_data)
            df.to_parquet(filepath, index=False)
        else:
            # Export as multiple parquet files in a directory
            if filepath is None:
                raise ValueError("filepath is required when single_file=False")
            dirpath = Path(filepath)
            dirpath.mkdir(parents=True, exist_ok=True)

            # Export nodes
            if output.node_labels:
                nodes_data = []
                for node_id in output.node_labels:
                    node = output.get_node(node_id)
                    if node:
                        nodes_data.append(node)
                if nodes_data:
                    df_nodes = pd.DataFrame(nodes_data)
                    df_nodes.to_parquet(dirpath / "nodes.parquet", index=False)

            # Export links
            if output.link_labels:
                links_data = []
                for link_id in output.link_labels:
                    link = output.get_link(link_id)
                    if link:
                        links_data.append(link)
                if links_data:
                    df_links = pd.DataFrame(links_data)
                    df_links.to_parquet(dirpath / "links.parquet", index=False)

            # Export subcatchments
            if output.subcatchment_labels:
                subcatch_data = []
                for subcatch_id in output.subcatchment_labels:
                    subcatch = output.get_subcatchment(subcatch_id)
                    if subcatch:
                        subcatch_data.append(subcatch)
                if subcatch_data:
                    df_subcatch = pd.DataFrame(subcatch_data)
                    df_subcatch.to_parquet(
                        dirpath / "subcatchments.parquet", index=False
                    )

            # Export summary
            summary = output.summary()
            summary_data = []
            for key, value in summary.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                summary_data.append({"field": key, "value": str(value)})

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_parquet(dirpath / "summary.parquet", index=False)
