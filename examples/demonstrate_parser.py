#!/usr/bin/env python3
"""
Comprehensive demonstration of enhanced SWMM report parser capabilities.
"""

from pathlib import Path
from swmm_utils import SwmmReport

print("=" * 80)
print("SWMM Report Parser - Comprehensive Feature Demonstration")
print("=" * 80)

# Use the Greenville model which has the most diverse features
rpt_path = Path("examples/example2/example2.rpt")

if not rpt_path.exists():
    print(f"\n⚠️  Report file not found: {rpt_path}")
    print("Please run example2.py first to generate the report file.")
    exit(1)

with SwmmReport(rpt_path) as report:
    print(f"\n{report}")
    print("-" * 80)

    # Header Information
    print(f"\n📋 HEADER INFORMATION")
    print(f"   Version: {report.header.get('version', 'N/A')}")
    print(f"   Build: {report.header.get('build', 'N/A')}")
    print(f"   Title: {report.header.get('title', 'N/A')}")

    # Analysis Options
    print(f"\n⚙️  ANALYSIS OPTIONS")
    opts = report.analysis_options
    print(f"   Flow Units: {opts.get('flow_units', 'N/A')}")
    print(f"   Routing Method: {opts.get('routing_method', 'N/A')}")
    print(f"   Start Date: {opts.get('start_date', 'N/A')}")
    print(f"   End Date: {opts.get('end_date', 'N/A')}")

    # Element Counts
    if report.element_count:
        print(f"\n📊 ELEMENT COUNT")
        for key, value in report.element_count.items():
            print(f"   {key.replace('_', ' ').title()}: {value}")

    # Continuity
    print(f"\n💧 CONTINUITY")
    for section_name, section_data in report.continuity.items():
        if section_data:
            print(f"   {section_name.replace('_', ' ').title()}:")
            if isinstance(section_data, dict):
                error = section_data.get("continuity_error")
                if error is not None:
                    print(f"     Error: {error}%")

    # Subcatchments
    if report.subcatchment_runoff:
        print(
            f"\n🌧️  SUBCATCHMENT RUNOFF ({len(report.subcatchment_runoff)} subcatchments)"
        )
        for i, sub in enumerate(report.subcatchment_runoff[:3]):
            print(f"   {i+1}. {sub['name']}")
            print(f"      Total Precip: {sub['total_precip']:.2f} in")
            print(f"      Total Runoff: {sub['total_runoff']:.2f} in")
            print(
                f"      Peak Runoff: {sub['peak_runoff']:.2f} {opts.get('flow_units', 'CFS')}"
            )
        if len(report.subcatchment_runoff) > 3:
            print(f"   ... and {len(report.subcatchment_runoff) - 3} more")

    # Nodes
    if report.node_depth:
        print(f"\n🔵 NODE DEPTH SUMMARY ({len(report.node_depth)} nodes)")
        # Find node with maximum depth
        max_node = max(report.node_depth, key=lambda x: x.get("maximum_depth", 0))
        print(
            f"   Maximum Depth: {max_node['maximum_depth']:.2f} ft at {max_node['name']}"
        )
        print(f"   Average Depth: {max_node.get('average_depth', 0):.2f} ft")
        print(
            f"   Time of Max: Day {max_node.get('time_of_max_days', 0)} {max_node.get('time_of_max', 'N/A')}"
        )

    # Node Surcharge
    if report.node_surcharge:
        print(f"\n⚠️  NODE SURCHARGE ({len(report.node_surcharge)} surcharged nodes)")
        for node in report.node_surcharge[:3]:
            print(
                f"   - {node['node_name']} ({node['node_type']}): {node['hours_surcharged']:.2f} hours"
            )
            print(f"     Height above crown: {node['max_height_above_crown']:.2f} ft")

    # Storage
    if report.storage_volume:
        print(f"\n🏪 STORAGE VOLUME ({len(report.storage_volume)} storage units)")
        for storage in report.storage_volume[:3]:
            print(f"   - {storage['storage_unit']}")
            print(f"     Max % Full: {storage['max_pct_full']:.1f}%")
            print(f"     Max Volume: {storage['max_volume']:.2f} 1000 ft³")
            if storage.get("max_outflow"):
                print(
                    f"     Max Outflow: {storage['max_outflow']:.2f} {opts.get('flow_units', 'CFS')}"
                )

    # Links
    if report.link_flow:
        print(f"\n🔗 LINK FLOW SUMMARY ({len(report.link_flow)} links)")
        # Find link with maximum flow
        max_link = max(report.link_flow, key=lambda x: x.get("maximum_flow", 0))
        print(
            f"   Maximum Flow: {max_link['maximum_flow']:.2f} {opts.get('flow_units', 'CFS')} at {max_link['name']}"
        )
        print(f"   Maximum Velocity: {max_link.get('maximum_velocity', 0):.2f} ft/s")
        if max_link.get("max_over_full_flow"):
            print(f"   Max/Full Flow: {max_link['max_over_full_flow']:.2f}")

    # Flow Classification
    if report.flow_classification:
        print(f"\n📈 FLOW CLASSIFICATION ({len(report.flow_classification)} conduits)")
        # Show statistics
        total_dry = sum(c.get("dry", 0) for c in report.flow_classification)
        avg_dry = (
            total_dry / len(report.flow_classification)
            if report.flow_classification
            else 0
        )
        print(f"   Average time dry: {avg_dry:.1f}%")

    # Pumps
    if report.pumping_summary:
        print(f"\n⚡ PUMPING SUMMARY ({len(report.pumping_summary)} pumps)")
        for pump in report.pumping_summary[:3]:
            print(f"   - {pump['pump_name']}")
            print(f"     Utilization: {pump['percent_utilized']:.1f}%")
            print(f"     Startups: {pump['num_startups']}")
            print(
                f"     Avg Flow: {pump['avg_flow']:.2f} {opts.get('flow_units', 'CFS')}"
            )
            print(f"     Power Usage: {pump['power_usage']:.2f} kW-hr")

    # LID Performance
    if report.lid_performance:
        print(f"\n🌱 LID PERFORMANCE ({len(report.lid_performance)} LID controls)")
        # Group by subcatchment
        subcatchments = {}
        for lid in report.lid_performance:
            sub = lid["subcatchment"]
            if sub not in subcatchments:
                subcatchments[sub] = []
            subcatchments[sub].append(lid)

        print(f"   Subcatchments with LID: {len(subcatchments)}")
        for sub, lids in list(subcatchments.items())[:2]:
            print(f"   - {sub}: {len(lids)} LID control(s)")
            for lid in lids[:2]:
                print(
                    f"     • {lid['lid_control']}: {lid['total_inflow']:.2f} in inflow, {lid['infil_loss']:.2f} in infiltrated"
                )

    # Water Quality
    if report.subcatchment_washoff:
        print(f"\n🧪 WATER QUALITY")
        print(
            f"   Subcatchment Washoff: {len(report.subcatchment_washoff)} subcatchments"
        )

    if report.link_pollutant_load:
        print(f"   Link Pollutant Load: {len(report.link_pollutant_load)} links")

    if report.quality_routing_continuity:
        print(
            f"   Quality Routing Continuity: {len(report.quality_routing_continuity)} fields"
        )

    # Groundwater
    if report.groundwater_summary:
        print(f"\n💦 GROUNDWATER")
        print(f"   {len(report.groundwater_summary)} data fields tracked")

    # Outfalls
    if report.outfall_loading:
        print(f"\n🚰 OUTFALL LOADING ({len(report.outfall_loading)} outfalls)")
        total_volume = sum(o.get("total_volume", 0) for o in report.outfall_loading)
        print(f"   Total System Volume: {total_volume:.3f} 10^6 gal")

    # Analysis Time
    if report.analysis_time:
        print(f"\n⏱️  ANALYSIS TIME")
        if "begun" in report.analysis_time:
            print(f"   Begun: {report.analysis_time['begun']}")
        if "ended" in report.analysis_time:
            print(f"   Ended: {report.analysis_time['ended']}")
        if "elapsed" in report.analysis_time:
            print(f"   Elapsed: {report.analysis_time['elapsed']}")

print("\n" + "=" * 80)
print("✅ Comprehensive demonstration complete!")
print("=" * 80)
