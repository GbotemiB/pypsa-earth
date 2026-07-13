# SPDX-FileCopyrightText: PyPSA-Earth and PyPSA-Eur Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MkDocs hook to automatically download validation results from the
pypsa-earth-status repository and generate the validation dashboard pages.
"""

import csv
import logging
import os
import urllib.request
from pathlib import Path

logger = logging.getLogger("mkdocs")

# TODO: Update to production repository URL after the pypsa-earth-status PR is merged.
CSV_URL = (
    "https://raw.githubusercontent.com/GbotemiB/pypsa-earth-status/"
    "health-status/results/health_status.csv"
)

# World boundaries GeoJSON for Leaflet
GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)


def make_markdown_table(headers, alignments, rows):
    """Generate a markdown table with custom alignment."""
    separator = []
    for align in alignments:
        if align == "right":
            separator.append("---:")
        elif align == "center":
            separator.append(":---:")
        else:
            separator.append(":---")
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(separator) + " |")
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(h, "")) for h in headers) + " |")
    return "\n".join(lines) + "\n"


def parse_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


CARRIER_COLORS = {
    "coal": "#374151",
    "ccgt": "#f97316",
    "gas": "#f97316",
    "oil": "#dc2626",
    "nuclear": "#c084fc",
    "pv": "#facc15",
    "solar": "#facc15",
    "wind": "#3b82f6",
    "hydro": "#06b6d4",
    "biomass": "#22c55e",
    "geothermal": "#b45309",
    "other": "#94a3b8",
}


def make_stacked_bar_html(mix_dict, unit):
    """
    Generate horizontal stacked bar charts in HTML for markdown page comparison.
    mix_dict: {carrier -> (pypsa_val, ref_val)}
    unit: 'MW' or 'TWh'
    """
    total_py = sum(val[0] for val in mix_dict.values())
    total_ref = sum(val[1] for val in mix_dict.values())

    if total_py <= 0 and total_ref <= 0:
        return ""

    # Sort carriers by reference value descending
    sorted_carriers = sorted(
        mix_dict.keys(), key=lambda c: mix_dict[c][1], reverse=True
    )

    # Render segments
    segments_py = []
    segments_ref = []
    legend_items = []

    for c in sorted_carriers:
        py_val, ref_val = mix_dict[c]
        color = CARRIER_COLORS.get(c.lower(), "#94a3b8")

        # PyPSA Segment
        if total_py > 0 and py_val > 0:
            pct_py = (py_val / total_py) * 100
            segments_py.append(
                f'<div style="width: {pct_py:.1f}%; background-color: {color}; height: 100%;" '
                f'title="{c.upper()}: {py_val:.1f} {unit} ({pct_py:.1f}%)"></div>'
            )

        # Ref Segment
        if total_ref > 0 and ref_val > 0:
            pct_ref = (ref_val / total_ref) * 100
            segments_ref.append(
                f'<div style="width: {pct_ref:.1f}%; background-color: {color}; height: 100%;" '
                f'title="{c.upper()}: {ref_val:.1f} {unit} ({pct_ref:.1f}%)"></div>'
            )

        # Legend
        if py_val > 0 or ref_val > 0:
            legend_items.append(
                f'<span style="display: inline-flex; align-items: center; margin-right: 12px; font-size: 11px; color: #475569;">'
                f'<i style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background-color: {color}; margin-right: 4px;"></i>'
                f"{c.upper()}"
                f"</span>"
            )

    py_bars = "".join(segments_py)
    ref_bars = "".join(segments_ref)
    legend_html = "".join(legend_items)

    html = f"""
<div style="margin: 16px 0; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px; background-color: #f8fafc; max-width: 600px;">
    <div style="display: flex; align-items: center; margin-bottom: 6px;">
        <span style="font-size: 11px; font-weight: 600; color: #64748b; width: 80px;">Model:</span>
        <div style="flex-grow: 1; display: flex; height: 16px; border-radius: 3px; overflow: hidden; background-color: #e2e8f0; border: 1px solid #cbd5e1;">
            {py_bars or '<div style="width: 100%; background-color: #e2e8f0; height: 100%; font-size: 9px; text-align: center; color: #94a3b8; line-height: 14px;">No Generation</div>'}
        </div>
        <span style="font-size: 11px; font-weight: 600; color: #334155; margin-left: 8px; width: 70px; text-align: right;">{total_py:.1f} {unit}</span>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 11px; font-weight: 600; color: #64748b; width: 80px;">Reference:</span>
        <div style="flex-grow: 1; display: flex; height: 16px; border-radius: 3px; overflow: hidden; background-color: #e2e8f0; border: 1px solid #cbd5e1;">
            {ref_bars or '<div style="width: 100%; background-color: #e2e8f0; height: 100%; font-size: 9px; text-align: center; color: #94a3b8; line-height: 14px;">No Generation</div>'}
        </div>
        <span style="font-size: 11px; font-weight: 600; color: #334155; margin-left: 8px; width: 70px; text-align: right;">{total_ref:.1f} {unit}</span>
    </div>
    <div style="display: flex; flex-wrap: wrap; margin-top: 8px; border-top: 1px solid #e2e8f0; padding-top: 6px;">
        {legend_html}
    </div>
</div>
"""
    return html


MAP_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyPSA-Earth Network Validation Map</title>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto+Mono&display=swap" rel="stylesheet">

    <style>
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: 'Inter', sans-serif;
            background-color: #f5f7fb;
        }

        #map {
            width: 100%;
            height: 100vh;
        }

        /* Premium Legend Control */
        .legend {
            padding: 12px 16px;
            font-family: 'Inter', sans-serif;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-radius: 8px;
            line-height: 24px;
            color: #333;
            border: 1px solid rgba(0,0,0,0.05);
        }
        .legend h4 {
            margin: 0 0 8px 0;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #555;
        }
        .legend i {
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.85;
            border-radius: 4px;
        }

        /* Popup styling */
        .leaflet-popup-content-wrapper {
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            font-family: 'Inter', sans-serif;
            padding: 4px;
            border: 1px solid rgba(0,0,0,0.05);
        }
        .leaflet-popup-content {
            margin: 12px 14px;
            line-height: 1.4;
        }
        .popup-header {
            margin: 0 0 10px 0;
            border-bottom: 1px solid #eee;
            padding-bottom: 6px;
        }
        .popup-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            color: #1e293b;
        }
        .popup-header span {
            font-size: 11px;
            color: #64748b;
            font-family: 'Roboto Mono', monospace;
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 4px;
        }

        /* Popup table styling */
        .popup-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }
        .popup-table th {
            text-align: left;
            padding: 6px 8px;
            background: #f8fafc;
            color: #475569;
            font-weight: 600;
            border-bottom: 1px solid #e2e8f0;
        }
        .popup-table td {
            padding: 6px 8px;
            border-bottom: 1px solid #f1f5f9;
            color: #334155;
        }
        .popup-table tr:last-child td {
            border-bottom: none;
        }

        /* Badges for grades */
        .grade-badge {
            font-family: 'Roboto Mono', monospace;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            text-align: center;
            font-size: 11px;
            display: inline-block;
        }
        .grade-a { background-color: #d1e7dd; color: #0f5132; }
        .grade-b { background-color: #e2f0d9; color: #385723; }
        .grade-c { background-color: #fff3cd; color: #664d03; }
        .grade-d { background-color: #f8d7da; color: #842029; }
        .grade-none { background-color: #f1f5f9; color: #64748b; }

        /* Loading indicator overlay */
        #loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.85);
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            font-family: 'Inter', sans-serif;
            transition: opacity 0.5s ease-out;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin-bottom: 12px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

    <div id="loading-overlay">
        <div class="spinner"></div>
        <div style="font-weight: 500; color: #475569;">Loading Validation Map Data...</div>
    </div>

    <div id="map"></div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

    <script>
        const CARRIER_COLORS = {
            "coal": "#374151",
            "ccgt": "#f97316",
            "gas": "#f97316",
            "oil": "#dc2626",
            "nuclear": "#c084fc",
            "pv": "#facc15",
            "solar": "#facc15",
            "wind": "#3b82f6",
            "hydro": "#06b6d4",
            "biomass": "#22c55e",
            "geothermal": "#b45309",
            "other": "#94a3b8"
        };

        function makeMixChartHTML(metrics, pillar, unit) {
            const rows = metrics.filter(m => m.pillar === pillar && (m.metric === "capacity" || m.metric === "generation"));
            if (rows.length === 0) return "";

            const sources = [...new Set(rows.map(r => r.reference_source))];
            let html = "";
            sources.forEach(src => {
                const srcRows = rows.filter(r => r.reference_source === src);
                let totalPy = 0;
                let totalRef = 0;
                const mix = {};

                srcRows.forEach(r => {
                    const py = r.pypsa_value ? parseFloat(r.pypsa_value) : 0;
                    const ref = r.reference_value ? parseFloat(r.reference_value) : 0;
                    mix[r.carrier] = [py, ref];
                    totalPy += py;
                    totalRef += ref;
                });

                if (totalPy <= 0 && totalRef <= 0) return;

                const sortedCarriers = Object.keys(mix).sort((a, b) => mix[b][1] - mix[a][1]);
                let pyBars = "";
                let refBars = "";
                let legendHtml = "";

                sortedCarriers.forEach(c => {
                    const [pyVal, refVal] = mix[c];
                    const color = CARRIER_COLORS[c.toLowerCase()] || "#94a3b8";

                    if (totalPy > 0 && pyVal > 0) {
                        const pctPy = (pyVal / totalPy) * 100;
                        pyBars += `<div style="width: ${pctPy.toFixed(1)}%; background-color: ${color}; height: 100%;" title="${c.toUpperCase()}: ${pyVal.toFixed(1)} ${unit} (${pctPy.toFixed(1)}%)"></div>`;
                    }
                    if (totalRef > 0 && refVal > 0) {
                        const pctRef = (refVal / totalRef) * 100;
                        refBars += `<div style="width: ${pctRef.toFixed(1)}%; background-color: ${color}; height: 100%;" title="${c.toUpperCase()}: ${refVal.toFixed(1)} ${unit} (${pctRef.toFixed(1)}%)"></div>`;
                    }
                    if (pyVal > 0 || refVal > 0) {
                        legendHtml += `
                            <span style="display: inline-flex; align-items: center; margin-right: 8px; font-size: 10px; color: #475569; margin-bottom: 2px;">
                                <i style="display: inline-block; width: 8px; height: 8px; border-radius: 1px; background-color: ${color}; margin-right: 3px;"></i>
                                ${c.toUpperCase()}
                            </span>
                        `;
                    }
                });

                const title = pillar === "installed_capacity" ? "Capacity Mix" : "Generation Mix";
                html += `
                    <div style="margin-top: 10px; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; background-color: #f8fafc; font-size: 11px;">
                        <div style="font-weight: 600; color: #334155; margin-bottom: 5px;">${title} (${src.toUpperCase()})</div>
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="color: #64748b; width: 65px; font-weight: 500;">Model:</span>
                            <div style="flex-grow: 1; display: flex; height: 12px; border-radius: 2px; overflow: hidden; background-color: #e2e8f0; border: 1px solid #cbd5e1;">
                                ${pyBars || '<div style="width: 100%; background-color: #e2e8f0; height: 100%;"></div>'}
                            </div>
                            <span style="color: #334155; margin-left: 6px; width: 60px; text-align: right; font-weight: 500;">${totalPy.toFixed(1)} ${unit}</span>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 6px;">
                            <span style="color: #64748b; width: 65px; font-weight: 500;">Reference:</span>
                            <div style="flex-grow: 1; display: flex; height: 12px; border-radius: 2px; overflow: hidden; background-color: #e2e8f0; border: 1px solid #cbd5e1;">
                                ${refBars || '<div style="width: 100%; background-color: #e2e8f0; height: 100%;"></div>'}
                            </div>
                            <span style="color: #334155; margin-left: 6px; width: 60px; text-align: right; font-weight: 500;">${totalRef.toFixed(1)} ${unit}</span>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 4px;">
                            ${legendHtml}
                        </div>
                    </div>
                `;
            });
            return html;
        }

        // 1. Initialize Map with Voyager style
        const map = L.map('map', {
            center: [15, 10],
            zoom: 2.5,
            minZoom: 2,
            maxBounds: [[-90, -180], [90, 180]]
        });

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        // 2. Simple CSV Parser
        function parseCSV(text) {
            const lines = text.split("\\n").filter(line => line.trim() !== "");
            if (lines.length === 0) return [];
            const headers = lines[0].split(",");
            return lines.slice(1).map(line => {
                const cols = [];
                let current = "";
                let inQuotes = false;
                for (let i = 0; i < line.length; i++) {
                    let char = line[i];
                    if (char === '"') {
                        inQuotes = !inQuotes;
                    } else if (char === ',' && !inQuotes) {
                        cols.push(current.trim());
                        current = "";
                    } else {
                        current += char;
                    }
                }
                cols.push(current.trim());
                const obj = {};
                headers.forEach((header, idx) => {
                    obj[header.trim()] = cols[idx];
                });
                return obj;
            });
        }

        // Color mapper for grades
        function getColorForGrade(grade) {
            switch (grade) {
                case 'A': return '#2e7d32'; // Green
                case 'B': return '#558b2f'; // Light Green/Olive
                case 'C': return '#ef6c00'; // Amber/Orange
                case 'D': return '#c62828'; // Red
                default: return '#78909c';  // Grey
            }
        }

        // 3. Load Data & Boundaries
        Promise.all([
            fetch('health_status.csv').then(res => {
                if (!res.ok) throw new Error("Local CSV not found");
                return res.text();
            }).catch(() => {
                console.log("Local CSV load failed; falling back to remote URL.");
                return fetch('__CSV_URL__').then(res => res.text());
            }),
            fetch('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson').then(res => res.json())
        ]).then(([csvText, geojsonData]) => {
            const records = parseCSV(csvText);

            // Group records by country code
            const countryData = {};
            records.forEach(r => {
                const code = r.country_code;
                if (!countryData[code]) {
                    countryData[code] = {
                        name: r.country_name,
                        scenario: r.scenario_key,
                        version: r.pypsa_earth_version,
                        year: r.year,
                        metrics: []
                    };
                }
                countryData[code].metrics.push(r);
            });

            // Calculate overall representative grade
            Object.keys(countryData).forEach(code => {
                const data = countryData[code];
                const totals = data.metrics.filter(m => m.metric.startsWith("total_"));
                const grades = totals.map(m => m.grade).filter(g => g && g !== "");

                if (grades.length > 0) {
                    const gradeValues = { 'A': 4, 'B': 3, 'C': 2, 'D': 1 };
                    const sum = grades.reduce((acc, g) => acc + (gradeValues[g] || 0), 0);
                    const avg = sum / grades.length;

                    let avgGrade = 'C';
                    if (avg >= 3.5) avgGrade = 'A';
                    else if (avg >= 2.5) avgGrade = 'B';
                    else if (avg >= 1.5) avgGrade = 'C';
                    else avgGrade = 'D';

                    data.avgGrade = avgGrade;
                } else {
                    data.avgGrade = 'None';
                }
            });

            // Remove loading indicator
            const loader = document.getElementById('loading-overlay');
            loader.style.opacity = 0;
            setTimeout(() => loader.remove(), 500);

            // Style GeoJSON country polygon
            function style(feature) {
                const code = feature.properties['ISO_A2'];
                const data = countryData[code];
                const color = data ? getColorForGrade(data.avgGrade) : '#cfd8dc';
                return {
                    fillColor: color,
                    weight: data ? 1.5 : 0.8,
                    opacity: 1,
                    color: '#ffffff',
                    fillOpacity: data ? 0.65 : 0.25
                };
            }

            // Hover and popup bindings
            function onEachFeature(feature, layer) {
                const code = feature.properties['ISO_A2'];
                const data = countryData[code];

                if (data) {
                    layer.on({
                        mouseover: function(e) {
                            const l = e.target;
                            l.setStyle({
                                fillOpacity: 0.85,
                                weight: 2
                            });
                            l.bringToFront();
                        },
                        mouseout: function(e) {
                            geojsonLayer.resetStyle(e.target);
                        }
                    });

                    layer.bindTooltip(
                        `<strong>${data.name}</strong><br/>Overall Grade: <span class="grade-badge grade-${data.avgGrade.toLowerCase()}">${data.avgGrade}</span>`,
                        { sticky: true }
                    );

                    let tableRows = "";
                    data.metrics.forEach(m => {
                        // Skip granular and MAE metrics from Totals table
                        if (m.metric === "capacity_mae_pct" || m.metric === "generation_share_mae" || m.metric === "capacity" || m.metric === "generation") {
                            return;
                        }

                        const val = m.pypsa_value ? parseFloat(m.pypsa_value).toFixed(1) : "-";

                        // Totals comparisons
                        const ref = m.reference_value ? parseFloat(m.reference_value).toFixed(1) : "-";
                        let dev = "-";
                        if (m.deviation_pct && m.deviation_pct !== "") {
                            const floatDev = parseFloat(m.deviation_pct);
                            dev = floatDev >= 0 ? `+${floatDev.toFixed(1)}%` : `${floatDev.toFixed(1)}%`;
                        }

                        const badgeClass = m.grade ? `grade-badge grade-${m.grade.toLowerCase()}` : 'grade-badge grade-none';
                        const displayGrade = m.grade || "-";
                        const unitLabel = m.unit === "%" ? "%" : m.unit;

                        let metricName = m.metric;
                        if (m.metric === "total_demand") metricName = "Total Demand";
                        else if (m.metric === "total_capacity") metricName = "Total Capacity";
                        else if (m.metric === "total_generation") metricName = "Total Gen";

                        const sourceName = m.reference_source.toUpperCase();

                        tableRows += `
                            <tr>
                                <td><strong>${metricName}</strong></td>
                                <td>${sourceName}</td>
                                <td>${val} ${unitLabel}</td>
                                <td>${ref} ${unitLabel === "%" ? "" : unitLabel}</td>
                                <td>${dev}</td>
                                <td><span class="${badgeClass}">${displayGrade}</span></td>
                            </tr>
                        `;
                    });

                    const capChart = makeMixChartHTML(data.metrics, "installed_capacity", "MW");
                    const genChart = makeMixChartHTML(data.metrics, "generation", "TWh");

                    const popupContent = `
                        <div class="popup-header">
                            <h3>${data.name} (${code})</h3>
                            <span>Scenario: ${data.scenario} | Year: ${data.year}</span>
                        </div>
                        <table class="popup-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Source</th>
                                    <th>Model</th>
                                    <th>Reference</th>
                                    <th>Deviation</th>
                                    <th>Grade</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows}
                            </tbody>
                        </table>
                        ${capChart}
                        ${genChart}
                        <div style="font-size: 10px; color: #94a3b8; text-align: right; margin-top: 8px;">
                            PyPSA-Earth Version: ${data.version}
                        </div>
                    `;

                    layer.bindPopup(popupContent, { maxWidth: 450 });
                }
            }

            const geojsonLayer = L.geoJSON(geojsonData, {
                style: style,
                onEachFeature: onEachFeature
            }).addTo(map);

            // Add Legend
            const legend = L.control({ position: 'bottomright' });
            legend.onAdd = function () {
                const div = L.DomUtil.create('div', 'info legend');
                const grades = ['A', 'B', 'C', 'D'];
                const labels = ['Excellent (A)', 'Good (B)', 'Moderate (C)', 'Poor (D)'];

                div.innerHTML = '<h4>Validation Status</h4>';
                for (let i = 0; i < grades.length; i++) {
                    div.innerHTML +=
                        '<i style="background:' + getColorForGrade(grades[i]) + '"></i> ' +
                        labels[i] + '<br/>';
                }
                div.innerHTML += '<i style="background:#78909c"></i> Unsolved / No Data';
                return div;
            };
            legend.addTo(map);

        }).catch(err => {
            console.error("Error loading map assets:", err);
            const overlay = document.getElementById('loading-overlay');
            overlay.innerHTML = `<div style="color: #ef4444; font-weight: 600;">Failed to Load Map: ${err.message}</div>`;
        });
    </script>
</body>
</html>
"""


def on_pre_build(config, **kwargs):
    """MkDocs hook: fetch validation data and generate dashboard pages."""
    logger.info("Validation Dashboard Hook: Starting build setup...")

    # Define paths
    docs_dir = Path(config["docs_dir"])
    val_dir = docs_dir / "validation"
    val_dir.mkdir(parents=True, exist_ok=True)

    csv_path = val_dir / "health_status.csv"
    map_path = val_dir / "health_status_map.html"
    dash_path = val_dir / "dashboard.md"
    overview_path = val_dir / "overview.md"
    statistics_path = val_dir / "statistics.md"

    # 1. Fetch CSV (only if not already present locally)
    if not csv_path.exists():
        try:
            logger.info(
                f"Validation Dashboard Hook: Fetching validation data from {CSV_URL}"
            )
            with urllib.request.urlopen(CSV_URL, timeout=10) as response:
                csv_data = response.read().decode("utf-8")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(csv_data)
            logger.info(
                "Validation Dashboard Hook: Successfully saved health_status.csv"
            )
        except Exception as e:
            logger.warning(
                f"Validation Dashboard Hook: Failed to download CSV ({e}). "
                "Falling back to existing local copy if available."
            )
            if not csv_path.exists():
                logger.error(
                    "Validation Dashboard Hook: No fallback CSV found! Skipping page generation."
                )
                return
    else:
        logger.info(
            "Validation Dashboard Hook: Using existing local copy of health_status.csv"
        )

    # 2. Parse CSV
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    if not records:
        logger.warning(
            "Validation Dashboard Hook: CSV file is empty! Skipping page generation."
        )
        return

    # Group by scenario key / country details
    groups = {}
    for r in records:
        key = (
            r["scenario_key"],
            r["country_code"],
            r["country_name"],
            r["pypsa_earth_version"],
            r["year"],
        )
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    # Sort groups by country name
    sorted_keys = sorted(groups.keys(), key=lambda k: k[2])

    # 3. Generate overview.md
    logger.info("Validation Dashboard Hook: Generating overview.md...")
    overview_rows = []
    for key in sorted_keys:
        scenario, country_code, country_name, version, year = key
        grp = groups[key]

        def format_grades(pillar, metric):
            grades = []
            for r in grp:
                if r["pillar"] == pillar and r["metric"] == metric:
                    grade = r["grade"]
                    src = r["reference_source"]
                    if grade and grade.strip():
                        grades.append(f"{grade} ({src})")
            return ", ".join(grades) if grades else "-"

        anchor_slug = f"{country_name.lower().replace(' ', '-')}-{country_code.lower()}-scenario-{scenario.lower()}"
        overview_rows.append(
            {
                "Scenario": scenario,
                "Country": f"[{country_name} ({country_code})](statistics.md#{anchor_slug})",
                "Demand Grade": format_grades("demand", "total_demand"),
                "Capacity Grade": format_grades("installed_capacity", "total_capacity"),
                "Generation Grade": format_grades("generation", "total_generation"),
                "PyPSA-Earth Version": version,
                "Year": year,
            }
        )

    headers = [
        "Scenario",
        "Country",
        "Demand Grade",
        "Capacity Grade",
        "Generation Grade",
        "PyPSA-Earth Version",
        "Year",
    ]
    alignments = ["left", "left", "left", "left", "left", "left", "right"]

    with open(overview_path, "w", encoding="utf-8") as f:
        f.write("# Validation Overview\n\n")
        f.write(
            "A summary of validation grades across all analyzed countries and scenarios. "
            "Grades assess the percentage deviation between model outputs and historical reference statistics (Ember, IRENA, OWID).\n\n"
        )
        f.write(make_markdown_table(headers, alignments, overview_rows))

    # 4. Generate statistics.md
    logger.info("Validation Dashboard Hook: Generating statistics.md...")
    with open(statistics_path, "w", encoding="utf-8") as f:
        f.write("# Detailed Validation Statistics\n\n")
        f.write(
            "Detailed comparisons of active validation scenarios. Metrics are grouped by country and pillar.\n\n"
        )

        for key in sorted_keys:
            scenario, country_code, country_name, version, year = key
            grp = groups[key]

            f.write(f"## {country_name} ({country_code}) — Scenario `{scenario}`\n\n")
            f.write(f"* **Model Year:** {year}\n")
            f.write(f"* **PyPSA-Earth Version:** `{version}`\n\n")

            # Demand section
            demand_rows = []
            for r in grp:
                if r["pillar"] == "demand":
                    py_val = parse_float(r["pypsa_value"])
                    ref_val = parse_float(r["reference_value"])
                    dev = parse_float(r["deviation_pct"])
                    dev_str = f"{dev:+.2f}%" if dev is not None else "-"

                    demand_rows.append(
                        {
                            "Source": r["reference_source"],
                            "Model Value (TWh)": (
                                f"{py_val:.2f}" if py_val is not None else "-"
                            ),
                            "Reference Value (TWh)": (
                                f"{ref_val:.2f}" if ref_val is not None else "-"
                            ),
                            "Deviation (%)": dev_str,
                            "Grade": r["grade"] if r["grade"] else "-",
                        }
                    )

            if demand_rows:
                f.write("### 1. Electricity Demand\n\n")
                f.write(
                    make_markdown_table(
                        [
                            "Source",
                            "Model Value (TWh)",
                            "Reference Value (TWh)",
                            "Deviation (%)",
                            "Grade",
                        ],
                        ["left", "right", "right", "left", "left"],
                        demand_rows,
                    )
                )
                f.write("\n")

            # Capacity section
            capacity_rows = []
            cap_mix = {}
            for r in grp:
                if r["pillar"] == "installed_capacity":
                    if r["metric"] == "total_capacity":
                        py_val = parse_float(r["pypsa_value"])
                        ref_val = parse_float(r["reference_value"])
                        dev = parse_float(r["deviation_pct"])
                        dev_str = f"{dev:+.2f}%" if dev is not None else "-"

                        capacity_rows.append(
                            {
                                "Source": r["reference_source"],
                                "Model Value (MW)": (
                                    f"{py_val:.2f}" if py_val is not None else "-"
                                ),
                                "Reference Value (MW)": (
                                    f"{ref_val:.2f}" if ref_val is not None else "-"
                                ),
                                "Deviation (%)": dev_str,
                                "Grade": r["grade"] if r["grade"] else "-",
                            }
                        )
                    elif r["metric"] == "capacity":
                        source = r["reference_source"]
                        carrier = r["carrier"]
                        py_val = parse_float(r["pypsa_value"]) or 0.0
                        ref_val = parse_float(r["reference_value"]) or 0.0
                        if source not in cap_mix:
                            cap_mix[source] = {}
                        cap_mix[source][carrier] = (py_val, ref_val)

            if capacity_rows:
                f.write("### 2. Installed Capacity\n\n")
                f.write("**Total Installed Capacity Comparison:**\n\n")
                f.write(
                    make_markdown_table(
                        [
                            "Source",
                            "Model Value (MW)",
                            "Reference Value (MW)",
                            "Deviation (%)",
                            "Grade",
                        ],
                        ["left", "right", "right", "left", "left"],
                        capacity_rows,
                    )
                )
                f.write("\n")

                for source, mix in cap_mix.items():
                    chart_html = make_stacked_bar_html(mix, "MW")
                    if chart_html:
                        f.write(f"**Installed Capacity Mix ({source.upper()}):**\n\n")
                        f.write(chart_html)
                        f.write("\n")

            # Generation section
            generation_rows = []
            gen_mix = {}
            for r in grp:
                if r["pillar"] == "generation":
                    if r["metric"] == "total_generation":
                        py_val = parse_float(r["pypsa_value"])
                        ref_val = parse_float(r["reference_value"])
                        dev = parse_float(r["deviation_pct"])
                        dev_str = f"{dev:+.2f}%" if dev is not None else "-"

                        generation_rows.append(
                            {
                                "Source": r["reference_source"],
                                "Model Value (TWh)": (
                                    f"{py_val:.2f}" if py_val is not None else "-"
                                ),
                                "Reference Value (TWh)": (
                                    f"{ref_val:.2f}" if ref_val is not None else "-"
                                ),
                                "Deviation (%)": dev_str,
                                "Grade": r["grade"] if r["grade"] else "-",
                            }
                        )
                    elif r["metric"] == "generation":
                        source = r["reference_source"]
                        carrier = r["carrier"]
                        py_val = parse_float(r["pypsa_value"]) or 0.0
                        ref_val = parse_float(r["reference_value"]) or 0.0
                        if source not in gen_mix:
                            gen_mix[source] = {}
                        gen_mix[source][carrier] = (py_val, ref_val)

            if generation_rows:
                f.write("### 3. Electricity Generation\n\n")
                f.write("**Total Generation Comparison:**\n\n")
                f.write(
                    make_markdown_table(
                        [
                            "Source",
                            "Model Value (TWh)",
                            "Reference Value (TWh)",
                            "Deviation (%)",
                            "Grade",
                        ],
                        ["left", "right", "right", "left", "left"],
                        generation_rows,
                    )
                )
                f.write("\n")

                for source, mix in gen_mix.items():
                    chart_html = make_stacked_bar_html(mix, "TWh")
                    if chart_html:
                        f.write(
                            f"**Electricity Generation Mix ({source.upper()}):**\n\n"
                        )
                        f.write(chart_html)
                        f.write("\n")

            f.write("---\n\n")

    # 5. Generate dashboard.md
    logger.info("Validation Dashboard Hook: Generating dashboard.md...")
    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(
            """# Validation Dashboard

This interactive map displays validation scores across all simulated country networks in the current run.

### Map Interaction
* **Hover:** Displays the overall country score grade.
* **Click:** Displays a detailed popup card with specific metric values (demand, capacity, and generation), deviations, and target validation datasets (Ember, IRENA, OWID).

---

<iframe src="../health_status_map.html" width="100%" height="650px" style="border: 1px solid #ddd; border-radius: 8px; background-color: #fdfdfd; box-shadow: 0 4px 12px rgba(0,0,0,0.05);"></iframe>

---

## Grade Definition
Model accuracy is evaluated using percentage deviations between simulated outputs and historical metrics:
* **Grade A (Dark Green):** Excellent fit (< 5% total deviation)
* **Grade B (Light Green):** Good fit (< 10% total deviation)
* **Grade C (Orange):** Moderate fit (< 20% total deviation)
* **Grade D (Red):** Poor fit (>= 20% total deviation)
"""
        )

    # 6. Generate health_status_map.html using template replacement to avoid f-string escaping issues
    logger.info("Validation Dashboard Hook: Generating health_status_map.html...")
    map_content = MAP_TEMPLATE.replace("__CSV_URL__", CSV_URL)
    with open(map_path, "w", encoding="utf-8") as f:
        f.write(map_content)

    logger.info("Validation Dashboard Hook: Successfully completed page compilation.")
