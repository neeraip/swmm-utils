"""
SWMM Utils Demo - Decode, Modify, and Encode SWMM Models

This example demonstrates:
1. Decoding a SWMM .inp file into a Python dict
2. Making modifications to the model
3. Encoding the modified model to .inp, .json, and .parquet formats
4. Decoding from JSON and Parquet formats back into memory
5. Round-trip conversion testing
"""

from pathlib import Path
from swmm_utils import SwmmInputDecoder, SwmmInputEncoder


def main():
    # Setup paths
    example_dir = Path(__file__).parent
    input_file = example_dir.parent / "data" / "10_Outfalls.inp"
    output_dir = example_dir / "output"

    print("=" * 80)
    print("SWMM Utils Demo - Decode, Modify, and Encode")
    print("=" * 80)

    # Step 1: Decode the SWMM input file
    print(f"\n📖 Step 1: Decoding SWMM file: {input_file.name}")
    decoder = SwmmInputDecoder()
    model = decoder.decode_file(str(input_file))

    print(f"   ✓ Successfully decoded!")
    print(f"   ✓ Model contains {len(model)} sections")

    # Show some stats about the model
    if "junctions" in model:
        print(f"   ✓ Junctions: {len(model['junctions'])}")
    if "outfalls" in model:
        print(f"   ✓ Outfalls: {len(model['outfalls'])}")
    if "conduits" in model:
        print(f"   ✓ Conduits: {len(model['conduits'])}")

    # Step 2: Make some modifications
    print(f"\n✏️  Step 2: Making modifications to the model")

    # Modify the title
    if "title" not in model or not model["title"]:
        model["title"] = "Modified SWMM Model - Demo Example"
    else:
        model["title"] = model["title"] + "\nModified by SWMM Utils Demo"
    print("   ✓ Updated title")

    # Add a comment to each junction (if they exist)
    if "junctions" in model and model["junctions"]:
        for junction in model["junctions"]:
            if "description" not in junction or not junction["description"]:
                junction["description"] = (
                    f"Modified junction: {junction.get('name', 'unknown')}"
                )
        print(f"   ✓ Added descriptions to {len(model['junctions'])} junctions")

    # Modify an option (if options exist)
    if "options" not in model:
        model["options"] = {}
    model["options"]["REPORT_STEP"] = "00:15:00"  # 15-minute reporting interval
    print("   ✓ Updated report step to 15 minutes")

    # Step 3: Encode to multiple formats
    print(f"\n💾 Step 3: Encoding model to multiple formats")
    encoder = SwmmInputEncoder()

    # 3a: Encode to .inp format
    inp_output = output_dir / "modified_model.inp"
    encoder.encode_to_inp_file(model, str(inp_output))
    print(f"   ✓ Saved .inp file: {inp_output}")

    # 3b: Encode to .json format
    json_output = output_dir / "modified_model.json"
    encoder.encode_to_json(model, str(json_output), pretty=True)
    print(f"   ✓ Saved .json file: {json_output}")

    # 3c: Encode to .parquet format (multi-file: one file per section)
    parquet_dir = output_dir / "parquet_multifile"
    encoder.encode_to_parquet(model, str(parquet_dir), single_file=False)
    print(f"   ✓ Saved .parquet files (multi-file): {parquet_dir}/")

    # Count parquet files created
    if parquet_dir.exists():
        parquet_files = list(parquet_dir.glob("*.parquet"))
        print(f"     → Created {len(parquet_files)} parquet files")

    # 3d: Encode to single .parquet file
    parquet_single = output_dir / "model_single.parquet"
    encoder.encode_to_parquet(model, str(parquet_single), single_file=True)
    print(f"   ✓ Saved .parquet file (single-file): {parquet_single}")
    if parquet_single.exists():
        size = parquet_single.stat().st_size
        print(f"     → File size: {size:,} bytes")

    # Step 4: Demonstrate using encode_to_file with format auto-detection
    print(f"\n🔄 Step 4: Using encode_to_file with format auto-detection")

    auto_inp = output_dir / "auto_detected.inp"
    encoder.encode_to_file(model, str(auto_inp))  # Format detected from .inp extension
    print(f"   ✓ Auto-detected .inp format: {auto_inp}")

    auto_json = output_dir / "auto_detected.json"
    encoder.encode_to_file(
        model, str(auto_json)
    )  # Format detected from .json extension
    print(f"   ✓ Auto-detected .json format: {auto_json}")

    # Step 5: Demonstrate decoding from JSON and Parquet
    print(f"\n🔄 Step 5: Decoding from JSON and Parquet formats")

    # 5a: Decode from JSON
    print(f"\n   Testing JSON decode:")
    json_model = decoder.decode_json(str(json_output))
    print(f"   ✓ Decoded from JSON: {len(json_model)} sections")

    # Verify it matches
    if "junctions" in json_model:
        print(f"     → Junctions: {len(json_model['junctions'])}")
    if json_model.get("title") == model.get("title"):
        print(f"     → Title matches original ✓")

    # 5b: Decode from Parquet (multi-file)
    print(f"\n   Testing Parquet decode (multi-file):")
    parquet_multifile_model = decoder.decode_parquet(str(parquet_dir))
    print(
        f"   ✓ Decoded from Parquet (multi-file): {len(parquet_multifile_model)} sections"
    )

    # Verify it matches
    if "junctions" in parquet_multifile_model:
        print(f"     → Junctions: {len(parquet_multifile_model['junctions'])}")
    if parquet_multifile_model.get("title") == model.get("title"):
        print(f"     → Title matches original ✓")

    # 5c: Decode from Parquet (single file)
    print(f"\n   Testing Parquet decode (single-file):")
    parquet_single_model = decoder.decode_parquet(str(parquet_single))
    print(
        f"   ✓ Decoded from Parquet (single-file): {len(parquet_single_model)} sections"
    )

    # Verify it matches
    if "junctions" in parquet_single_model:
        print(f"     → Junctions: {len(parquet_single_model['junctions'])}")
    if parquet_single_model.get("title") == model.get("title"):
        print(f"     → Title matches original ✓")

    # 5c: Round-trip test: encode to JSON, decode, and re-encode
    print(f"\n   Testing round-trip (JSON → decode → encode → JSON):")
    roundtrip_json = output_dir / "roundtrip.json"
    encoder.encode_to_json(json_model, str(roundtrip_json), pretty=True)
    print(f"   ✓ Round-trip successful: {roundtrip_json}")

    # Summary
    print(f"\n" + "=" * 80)
    print("✅ Demo completed successfully!")
    print("=" * 80)
    print(f"\nOutput files saved to: {output_dir}")
    print("\nGenerated files:")
    for output_file in sorted(output_dir.rglob("*")):
        if output_file.is_file():
            size = output_file.stat().st_size
            print(f"  • {output_file.relative_to(output_dir)} ({size:,} bytes)")
    print()


if __name__ == "__main__":
    main()
