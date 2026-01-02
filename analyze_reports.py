#!/usr/bin/env python3
"""
Script to run SWMM simulations on diverse .inp files and analyze the resulting .rpt files.
"""

import multiprocessing
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Select diverse .inp files to test different SWMM features
test_files = [
    # Different sizes
    "10_Outfalls.inp",  # Small model
    "1000_NODE.inp",  # Medium model
    # Different routing methods
    "100_Control_Rules.inp",  # Control rules
    "108_Pumps_FM.inp",  # Force mains and pumps
    "13_Orifices.inp",  # Orifices
    "14_Pumps.inp",  # Pumps
    "15_Storage_Nodes.inp",  # Storage nodes
    "133_Weirs.inp",  # Weirs
    # Different infiltration methods
    "125_Subs_Horton.inp",  # Horton
    "27_Subs_Horton.inp",  # Horton
    "25_Subcatchments_CN_Infiltration.inp",  # Curve Number
    "Green_Ampt_Impervious_Watershed_Example.inp",  # Green-Ampt
    # Different units
    "15_Subs_SI_Units.inp",  # SI Units
    "117_H&H_Elements_SI_Units.inp",  # SI Units
    "1050_H&H_SI_Units.inp",  # SI Units
    # Water quality
    "1000yearSimulation_Case0_wq.inp",  # WQ
    "1500_H&H_Elements_w7_WQ.inp",  # WQ
    # LID controls
    "8_LID_Example_8_Subs.inp",  # LID
    "8_LID_Example_8_Subs_Continuous.inp",  # LID continuous
    "Greenville_6LIDControls_All_LID_Usage.inp",  # LID
    # RDII
    "1084_Nodes_84_RDII_SI_Units.inp",  # RDII
    "2227_Nodes_RDII.inp",  # RDII
    # Groundwater
    "5320_GW.inp",  # Groundwater
    "Large_GW.inp",  # Large groundwater
    # Snowmelt
    "GreenvilleSnowmelt.inp",  # Snowmelt
    "Small_SnowPack_Model.inp",  # Snowmelt
    # Special features
    "Greenville_all_SWMM5_Features.inp",  # All features
    "DUPUIT-FORCHHEIMER APPROXIMATION FOR SUBSURFACE Flow.inp",  # Subsurface flow
    "dual_drainage.inp",  # Dual drainage
    # Different flow routing
    "Linear_Force_Main.inp",  # Linear
    "many_Natural_Channels.inp",  # Natural channels
    "Trapezoidal_Channel_SW5_SI_Units.inp",  # Trapezoidal
]

data_dir = Path("data")
bin_dir = Path("bin")
runswmm = bin_dir / "runswmm"

# Get number of CPU cores
num_cores = multiprocessing.cpu_count()
print(f"💻 Detected {num_cores} CPU cores")

if not runswmm.exists():
    print(f"Error: {runswmm} not found")
    sys.exit(1)


def optimize_inp_threads(inp_path: Path, num_threads: int) -> Path:
    """
    Create a temporary .inp file with optimized THREADS setting.

    Args:
        inp_path: Path to original .inp file
        num_threads: Number of threads to use

    Returns:
        Path to temporary .inp file with optimized settings
    """
    with open(inp_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Check if OPTIONS section exists
    if "[OPTIONS]" in content:
        # Split into sections
        parts = content.split("[OPTIONS]")
        before_options = parts[0]
        after_options = parts[1]

        # Find the end of OPTIONS section (next section or end of file)
        next_section_idx = after_options.find("\n[")
        if next_section_idx != -1:
            options_content = after_options[:next_section_idx]
            after_sections = after_options[next_section_idx:]
        else:
            options_content = after_options
            after_sections = ""

        # Update or add THREADS setting
        lines = options_content.split("\n")
        threads_found = False
        updated_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("THREADS"):
                # Replace existing THREADS setting
                updated_lines.append(f"THREADS              {num_threads}")
                threads_found = True
            else:
                updated_lines.append(line)

        # If THREADS not found, add it
        if not threads_found:
            # Insert after first non-empty line in OPTIONS
            for i, line in enumerate(updated_lines):
                if line.strip():
                    updated_lines.insert(i + 1, f"THREADS              {num_threads}")
                    break

        # Reconstruct content
        content = (
            before_options + "[OPTIONS]" + "\n".join(updated_lines) + after_sections
        )
    else:
        # No OPTIONS section, add one at the beginning
        content = f"[OPTIONS]\nTHREADS              {num_threads}\n\n" + content

    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".inp", text=True)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        return Path(temp_path)
    except:
        os.close(temp_fd)
        raise


print(f"Running {len(test_files)} simulations...")
print("=" * 80)

successful = []
failed = []

for inp_file in test_files:
    inp_path = data_dir / inp_file

    if not inp_path.exists():
        print(f"⚠️  Skipping {inp_file} - file not found")
        failed.append((inp_file, "File not found"))
        continue

    # Generate output file names
    base_name = inp_path.stem
    rpt_path = data_dir / f"{base_name}.rpt"
    out_path = data_dir / f"{base_name}.out"

    print(f"\n📄 {inp_file}")

    # Create optimized temporary .inp file
    temp_inp = None
    try:
        temp_inp = optimize_inp_threads(inp_path, num_cores)
        print(f"   ⚙️  Created temp file with THREADS={num_cores}")
        print(f"   Running simulation...")

        # Run SWMM simulation with optimized file
        result = subprocess.run(
            [str(runswmm), str(temp_inp), str(rpt_path), str(out_path)],
            capture_output=True,
            text=True,
            timeout=120,  # 120 second timeout
        )

        if result.returncode == 0 and rpt_path.exists():
            # Check file size
            rpt_size = rpt_path.stat().st_size
            print(f"   ✅ Success - Report: {rpt_size:,} bytes")
            successful.append((inp_file, rpt_size))
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            print(f"   ❌ Failed - {error_msg}")
            failed.append((inp_file, error_msg))

    except subprocess.TimeoutExpired:
        print(f"   ⏱️  Timeout (>120s)")
        failed.append((inp_file, "Timeout"))
    except Exception as e:
        print(f"   ❌ Error: {e}")
        failed.append((inp_file, str(e)))
    finally:
        # Clean up temporary file
        if temp_inp and temp_inp.exists():
            temp_inp.unlink()

print("\n" + "=" * 80)
print(f"\n📊 Summary:")
print(f"   Successful: {len(successful)}")
print(f"   Failed: {len(failed)}")

if successful:
    print(f"\n✅ Successful simulations:")
    for inp_file, size in successful:
        print(f"   - {inp_file} ({size:,} bytes)")

if failed:
    print(f"\n❌ Failed simulations:")
    for inp_file, reason in failed:
        print(f"   - {inp_file}: {reason[:50]}")

print(f"\n💾 Report files generated in: {data_dir}")
