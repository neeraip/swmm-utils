"""
example1 Example - Load .inp, run SWMM simulation, and convert to JSON and Parquet

This example demonstrates:
1. Loading a SWMM .inp file
2. Running the SWMM simulation engine
3. Outputting to JSON format
4. Outputting to Parquet format (both single-file and multi-file modes)
5. Parsing the SWMM report (.rpt) file
6. Parsing the SWMM output (.out) binary file
"""

import subprocess
from pathlib import Path
from swmm_utils import SwmmInput, SwmmReport, SwmmOutput


def main():
    # Setup paths
    example_dir = Path(__file__).parent
    input_file = example_dir / "example1.inp"
    report_file = example_dir / "example1.rpt"
    output_file = example_dir / "example1.out"
    output_dir = example_dir  # Output to the same folder as the script

    # Path to runswmm executable
    bin_dir = example_dir.parent.parent / "bin"
    runswmm = bin_dir / "runswmm"

    print("=" * 80)
    print("example1 Example - Load, Simulate, and Convert SWMM Model")
    print("=" * 80)

    # Load the SWMM input file
    print(f"\n📖 Loading SWMM file: {input_file.name}")

    with SwmmInput(input_file) as inp:
        print(f"   ✓ Successfully loaded!")
        print(f"   ✓ Model title: {inp.title}")
        print(f"   ✓ Model contains {len(list(inp.keys()))} sections")

        # Show model statistics
        if inp.subcatchments:
            print(f"   ✓ Subcatchments: {len(inp.subcatchments)}")
        if inp.junctions:
            print(f"   ✓ Junctions: {len(inp.junctions)}")
        if inp.outfalls:
            print(f"   ✓ Outfalls: {len(inp.outfalls)}")
        if inp.conduits:
            print(f"   ✓ Conduits: {len(inp.conduits)}")

        # Output to JSON
        print(f"\n💾 Saving to JSON format")
        json_output = output_dir / "example1.inp.json"
        inp.to_json(json_output, pretty=True)

        if json_output.exists():
            size = json_output.stat().st_size
            print(f"   ✓ Saved: {json_output}")
            print(f"   ✓ Size: {size:,} bytes")

        # Output to Parquet (multi-file mode)
        print(f"\n💾 Saving to Parquet format (multi-file)")
        parquet_dir = output_dir / "example1.inp_parquet"
        inp.to_parquet(parquet_dir, single_file=False)

        if parquet_dir.exists():
            parquet_files = list(parquet_dir.glob("*.parquet"))
            total_size = sum(f.stat().st_size for f in parquet_files)
            print(f"   ✓ Saved: {parquet_dir}/")
            print(f"   ✓ Files created: {len(parquet_files)}")
            print(f"   ✓ Total size: {total_size:,} bytes")

        # Output to Parquet (single-file mode)
        print(f"\n💾 Saving to Parquet format (single-file)")
        parquet_file = output_dir / "example1.inp.parquet"
        inp.to_parquet(parquet_file, single_file=True)

        if parquet_file.exists():
            size = parquet_file.stat().st_size
            print(f"   ✓ Saved: {parquet_file}")
            print(f"   ✓ Size: {size:,} bytes")

    # Run SWMM simulation
    print(f"\n🚀 Running SWMM simulation")
    print(f"   Input: {input_file.name}")
    print(f"   Report: {report_file.name}")
    print(f"   Output: {output_file.name}")

    try:
        result = subprocess.run(
            [str(runswmm), str(input_file), str(report_file), str(output_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"   ✓ Simulation completed successfully!")

        if report_file.exists():
            rpt_size = report_file.stat().st_size
            print(f"   ✓ Report generated: {report_file.name} ({rpt_size:,} bytes)")

        if output_file.exists():
            out_size = output_file.stat().st_size
            print(f"   ✓ Output generated: {output_file.name} ({out_size:,} bytes)")

    except subprocess.CalledProcessError as e:
        print(f"   ✗ Simulation failed with exit code {e.returncode}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
    except FileNotFoundError:
        print(f"   ✗ Could not find runswmm executable at {runswmm}")

    # Parse report file
    if report_file.exists():
        print(f"\n📊 Parsing SWMM report file")
        with SwmmReport(report_file) as report:
            print(f"   ✓ Successfully parsed!")
            print(f"   ✓ SWMM Version: {report.header.get('version', 'Unknown')}")
            print(f"   ✓ Analysis Options:")
            print(
                f"      - Flow Units: {report.analysis_options.get('flow_units', 'N/A')}"
            )
            print(
                f"      - Routing Method: {report.analysis_options.get('flow_routing_method', 'N/A')}"
            )

            # Show node depth summary
            if report.node_depth:
                print(f"\n   💧 Node Depth Summary:")
                for node in report.node_depth:
                    print(
                        f"      {node['name']} ({node['type']}): {node['maximum_depth']:.2f} ft max depth"
                    )

            # Show link flow summary
            if report.link_flow:
                print(f"\n   🌊 Link Flow Summary:")
                for link in report.link_flow:
                    print(
                        f"      {link['name']}: {link['maximum_flow']:.2f} CFS max flow, {link['maximum_velocity']:.2f} ft/s max velocity"
                    )

    # Parse output file
    if output_file.exists():
        print(f"\n💾 Parsing SWMM output file")
        try:
            out = SwmmOutput(output_file)
            print(f"   ✓ Successfully parsed!")
            print(f"   ✓ SWMM Version: {out.version}")
            print(f"   ✓ Flow Unit: {out.flow_unit}")
            print(
                f"   ✓ Simulation Period: {out.start_date.strftime('%Y-%m-%d %H:%M:%S')} to {out.end_date.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(f"   ✓ Report Interval: {out.report_interval}")
            print(f"   ✓ Time Steps: {out.n_periods}")

            # Show model summary
            summary = out.summary()
            print(f"\n   📋 Model Summary:")
            print(f"      - Subcatchments: {summary['n_subcatchments']}")
            print(f"      - Nodes: {summary['n_nodes']}")
            print(f"      - Links: {summary['n_links']}")
            print(f"      - Pollutants: {summary['n_pollutants']}")
            if summary["pollutants"]:
                print(f"      - Pollutant List: {', '.join(summary['pollutants'])}")

            # Export output to JSON
            print(f"\n   💾 Saving output metadata to JSON format")
            out_json = output_dir / "example1.out.json"
            out.to_json(out_json, pretty=True)
            if out_json.exists():
                size = out_json.stat().st_size
                print(f"      ✓ Saved: {out_json.name} ({size:,} bytes)")

            # Export output to Parquet (single file)
            print(f"\n   💾 Saving output metadata to Parquet format (single-file)")
            out_parquet = output_dir / "example1.out.parquet"
            try:
                out.to_parquet(out_parquet, single_file=True)
                if out_parquet.exists():
                    size = out_parquet.stat().st_size
                    print(f"      ✓ Saved: {out_parquet.name} ({size:,} bytes)")
            except ImportError:
                print(f"      ⚠ pandas/pyarrow not installed, skipping Parquet export")

            # Export output to Parquet (multi-file)
            print(f"\n   💾 Saving output metadata to Parquet format (multi-file)")
            out_parquet_dir = output_dir / "example1.out_parquet"
            try:
                out.to_parquet(out_parquet_dir, single_file=False)
                if out_parquet_dir.exists():
                    parquet_files = list(out_parquet_dir.glob("*.parquet"))
                    total_size = sum(f.stat().st_size for f in parquet_files)
                    print(f"      ✓ Saved: {out_parquet_dir.name}/")
                    print(f"      ✓ Files created: {len(parquet_files)}")
                    print(f"      ✓ Total size: {total_size:,} bytes")
            except ImportError:
                print(f"      ⚠ pandas/pyarrow not installed, skipping Parquet export")

        except Exception as e:
            print(f"   ✗ Failed to parse output file: {e}")

    # Summary
    print(f"\n" + "=" * 80)
    print("✅ Example completed successfully!")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    for output_file_path in sorted(output_dir.rglob("*")):
        if output_file_path.is_file():
            size = output_file_path.stat().st_size
            rel_path = output_file_path.relative_to(output_dir)
            print(f"  • {rel_path} ({size:,} bytes)")
    print()


if __name__ == "__main__":
    main()
