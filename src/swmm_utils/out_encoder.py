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

    def encode_to_dataframe(
        self,
        data: Dict[str, Any],
        element_type: Optional[str] = None,
        element_name: Optional[str] = None,
    ):
        """
        Export output file data to Pandas DataFrame(s).

        Supports three levels of export:
        - Full export (no args): Returns dict with metadata and time series sections
        - Section export (element_type only): Returns MultiIndex DataFrame for that section
        - Single element (both args): Returns single element time series as DataFrame

        Args:
            data: Output data dictionary from SwmmOutputDecoder.decode_file()
            element_type: 'nodes', 'links', or 'subcatchments'. If None, exports all.
            element_name: Specific element name. Requires element_type.

        Returns:
            - Full export: Dict with keys 'metadata', 'nodes', 'links', 'subcatchments'
            - Section export: MultiIndex DataFrame (timestamp, element_name)
            - Single element: DataFrame with timestamp index

        Raises:
            ValueError: If element_name provided without element_type
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for DataFrame export. Install with: pip install pandas"
            ) from exc

        # Validate inputs
        if element_name is not None and element_type is None:
            raise ValueError(
                "element_type must be specified when element_name is provided"
            )

        # Check if time series data is available
        if data.get("time_series") is None:
            if element_type is None:
                # Full export - return dict with empty sections
                return {
                    "metadata": pd.DataFrame([data["metadata"]]),
                    "nodes": pd.DataFrame(),
                    "links": pd.DataFrame(),
                    "subcatchments": pd.DataFrame(),
                }
            # Section export - return empty DataFrame
            return pd.DataFrame()

        time_series = data["time_series"]
        time_index = data.get("time_index", [])

        # Full export: return dict with all sections
        if element_type is None:
            metadata_df = pd.DataFrame(
                [
                    {
                        "version": data["header"]["version_str"],
                        "flow_unit": data["header"]["flow_unit"],
                        "n_subcatchments": data["header"]["n_subcatchments"],
                        "n_nodes": data["header"]["n_nodes"],
                        "n_links": data["header"]["n_links"],
                        "n_pollutants": data["header"]["n_pollutants"],
                        "start_date": data["metadata"]["start_date"],
                        "report_interval_seconds": data["metadata"][
                            "report_interval_seconds"
                        ],
                        "n_periods": data["metadata"]["n_periods"],
                    }
                ]
            )

            return {
                "metadata": metadata_df,
                "nodes": self._build_section_dataframe(
                    time_series, "nodes", data["metadata"]["labels"]["node"], time_index
                ),
                "links": self._build_section_dataframe(
                    time_series, "links", data["metadata"]["labels"]["link"], time_index
                ),
                "subcatchments": self._build_section_dataframe(
                    time_series,
                    "subcatchments",
                    data["metadata"]["labels"]["subcatchment"],
                    time_index,
                ),
            }

        # Single element export
        if element_name is not None:
            return self._build_element_dataframe(
                time_series, element_type, element_name, time_index
            )

        # Section export: return MultiIndex DataFrame
        label_key = {
            "nodes": "node",
            "links": "link",
            "subcatchments": "subcatchment",
        }.get(element_type)

        if label_key is None:
            raise ValueError(
                f"Invalid element_type: {element_type}. "
                "Must be 'nodes', 'links', or 'subcatchments'."
            )

        # Map element_type to time series key (plural)
        ts_key = {
            "nodes": "nodes",
            "links": "links",
            "subcatchments": "subcatchments",
        }[element_type]

        return self._build_section_dataframe(
            time_series, ts_key, data["metadata"]["labels"][label_key], time_index
        )

    def _build_section_dataframe(
        self, time_series: Dict[str, Any], element_type: str, labels: list, time_index: list
    ):
        """Build MultiIndex DataFrame for a section (nodes, links, subcatchments).

        Args:
            time_series: Time series data dict
            element_type: 'nodes', 'links', or 'subcatchments'
            labels: List of element labels/names
            time_index: List of timestamps

        Returns:
            MultiIndex DataFrame with (timestamp, element_name) index
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for DataFrame export. Install with: pip install pandas"
            ) from exc

        rows = []

        # Get the element data for this type
        element_data = time_series.get(element_type, {})

        # Iterate through each element
        for element_name in labels:
            if element_name not in element_data:
                continue

            element_ts = element_data[element_name]

            # Iterate through each timestamp
            for time_idx, timestamp in enumerate(time_index):
                if time_idx >= len(element_ts):
                    break

                # Extract values from the record
                timestamp_record = element_ts[time_idx]
                values = timestamp_record.get("values", [])

                # Add row for this element at this timestamp
                row = {"timestamp": timestamp, "element_name": element_name}

                # Add value columns with generic names if we don't have specific names
                for val_idx, value in enumerate(values):
                    row[f"value_{val_idx}"] = value

                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Set MultiIndex (timestamp, element_name)
        df = df.set_index(["timestamp", "element_name"])

        return df

    def _build_element_dataframe(
        self, time_series: Dict[str, Any], element_type: str, element_name: str, time_index: list
    ):
        """Build DataFrame for a single element's full time series.

        Args:
            time_series: Time series data dict
            element_type: 'nodes', 'links', or 'subcatchments'
            element_name: Specific element name
            time_index: List of timestamps

        Returns:
            DataFrame with timestamp index
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for DataFrame export. Install with: pip install pandas"
            ) from exc

        # element_type is already plural (nodes, links, subcatchments)
        ts_key = element_type

        element_data = time_series.get(ts_key, {})

        if element_name not in element_data:
            return pd.DataFrame()

        element_ts = element_data[element_name]

        if len(element_ts) != len(time_index):
            return pd.DataFrame()

        # Build rows with each property value at each timestamp
        rows = []
        for time_idx, timestamp in enumerate(time_index):
            row = {"timestamp": timestamp}

            # Extract values from the record
            timestamp_record = element_ts[time_idx]
            values = timestamp_record.get("values", [])

            # Add value columns with generic names
            for val_idx, value in enumerate(values):
                row[f"value_{val_idx}"] = value

            rows.append(row)

        df = pd.DataFrame(rows)

        # Set timestamp as index
        df = df.set_index("timestamp")

        return df
