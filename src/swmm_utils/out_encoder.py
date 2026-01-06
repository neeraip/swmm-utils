"""SWMM output file encoder - encode SWMM output data to .json or .parquet formats."""

import json
from typing import Any, Callable, Dict, Optional, Union
from pathlib import Path


class SwmmOutputEncoder:
    """Encode SWMM output data to .json or .parquet formats."""

    def encode_to_file(
        self,
        data: Dict[str, Any],
        filepath: Union[str, Path],
        file_format: Optional[str] = None,
        summary_func: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """Encode SWMM output to a file.

        Args:
            data: Output data dictionary from SwmmOutputDecoder.decode_file()
            filepath: Output file path
            file_format: Output format ('json', 'parquet'). If None, inferred from filepath extension.
            summary_func: Optional callable to generate summary dict
        """
        if file_format is None:
            # Infer format from file extension
            ext = Path(filepath).suffix.lower()
            format_map = {".json": "json", ".parquet": "parquet"}
            file_format = format_map.get(ext, "json")

        if file_format == "json":
            self.encode_to_json(data, filepath, pretty=True, summary_func=summary_func)
        elif file_format == "parquet":
            self.encode_to_parquet(data, filepath, summary_func=summary_func)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    def encode_to_json(
        self,
        data: Dict[str, Any],
        filepath: Union[str, Path],
        pretty: bool = True,
        summary_func: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """
        Export output file data to JSON format.

        Exports all data that was loaded during initialization.
        If initialized with load_time_series=False (default), exports only metadata.
        If initialized with load_time_series=True, exports metadata and all time series data.

        Args:
            data: Output data dictionary from SwmmOutputDecoder.decode_file()
            filepath: Path where JSON file will be saved
            pretty: Whether to pretty-print JSON (default True)
            summary_func: Optional callable to generate summary dict
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "header": data["header"],
            "metadata": {
                "labels": data["metadata"]["labels"],
                "pollutant_units": data["metadata"]["pollutant_units"],
                "properties": data["metadata"]["properties"],
                "variables": data["metadata"]["variables"],
                "start_date": data["metadata"]["start_date"].isoformat(),
                "report_interval_seconds": data["metadata"]["report_interval_seconds"],
                "n_periods": data["metadata"]["n_periods"],
            },
        }

        # Add summary if provided
        if summary_func is not None:
            output_data["summary"] = summary_func()

        # Add time series if it was loaded
        if data.get("time_series") is not None:
            output_data["time_series"] = data["time_series"]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                output_data,
                f,
                indent=2 if pretty else None,
                ensure_ascii=False,
            )

    def encode_to_parquet(
        self,
        data: Dict[str, Any],
        filepath: Union[str, Path, None] = None,
        single_file: bool = True,
        summary_func: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        """
        Export output file metadata to Parquet format.

        Args:
            data: Output data dictionary from SwmmOutputDecoder.decode_file()
            filepath: Path where Parquet file will be saved. If single_file=False,
                     this is treated as a directory path.
            single_file: Whether to save as single file (True) or multiple files (False).
                        If False, creates separate parquet files for each data type.
            summary_func: Optional callable to generate summary dict
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
            summary = summary_func() if summary_func is not None else {}

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

            node_labels = data["metadata"]["labels"]["node"]
            link_labels = data["metadata"]["labels"]["link"]
            subcatch_labels = data["metadata"]["labels"]["subcatchment"]
            node_props = data["metadata"]["properties"]["node"]
            link_props = data["metadata"]["properties"]["link"]
            subcatch_props = data["metadata"]["properties"]["subcatchment"]

            # Export nodes
            if node_labels:
                nodes_data = []
                for node_id in node_labels:
                    if node_id in node_props:
                        nodes_data.append({"id": node_id, **node_props[node_id]})
                if nodes_data:
                    df_nodes = pd.DataFrame(nodes_data)
                    df_nodes.to_parquet(dirpath / "nodes.parquet", index=False)

            # Export links
            if link_labels:
                links_data = []
                for link_id in link_labels:
                    if link_id in link_props:
                        links_data.append({"id": link_id, **link_props[link_id]})
                if links_data:
                    df_links = pd.DataFrame(links_data)
                    df_links.to_parquet(dirpath / "links.parquet", index=False)

            # Export subcatchments
            if subcatch_labels:
                subcatch_data = []
                for subcatch_id in subcatch_labels:
                    if subcatch_id in subcatch_props:
                        subcatch_data.append(
                            {"id": subcatch_id, **subcatch_props[subcatch_id]}
                        )
                if subcatch_data:
                    df_subcatch = pd.DataFrame(subcatch_data)
                    df_subcatch.to_parquet(
                        dirpath / "subcatchments.parquet", index=False
                    )

            # Export summary
            summary = summary_func() if summary_func is not None else {}
            summary_data = []
            for key, value in summary.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                summary_data.append({"field": key, "value": str(value)})

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_parquet(dirpath / "summary.parquet", index=False)
