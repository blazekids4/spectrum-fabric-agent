"""
Visualization utilities for Fabric competitor analysis data
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from datetime import datetime

def setup_plotting_style():
    """Configure plotting style for consistent visualizations."""
    sns.set(style="whitegrid")
    plt.rcParams["figure.figsize"] = (12, 8)
    plt.rcParams["font.size"] = 12
    
    # Use a professional color palette
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
              "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    sns.set_palette(sns.color_palette(colors))

def create_competitor_frequency_chart(data_path, output_dir="visualizations"):
    """
    Create a bar chart showing frequency of competitor mentions.
    
    Args:
        data_path (str): Path to normalized data CSV
        output_dir (str): Directory to save visualizations
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    data = pd.read_csv(data_path)
    
    # Count competitor mentions
    competitor_counts = data["competitor_canonical"].value_counts()
    
    # Create plot
    plt.figure(figsize=(14, 8))
    ax = sns.barplot(x=competitor_counts.index, y=competitor_counts.values)
    
    # Customize plot
    plt.title("Frequency of Competitor Mentions in Call Transcripts", fontsize=16)
    plt.xlabel("Competitor", fontsize=14)
    plt.ylabel("Number of Mentions", fontsize=14)
    plt.xticks(rotation=45, ha="right")
    
    # Add value labels on bars
    for i, v in enumerate(competitor_counts.values):
        ax.text(i, v + 5, str(v), ha='center', fontsize=12)
    
    plt.tight_layout()
    
    # Save plot
    output_path = os.path.join(output_dir, "competitor_frequency.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved competitor frequency chart to {output_path}")
    
    return output_path

def create_competitor_timeline(data_path, output_dir="visualizations"):
    """
    Create a line chart showing competitor mentions over time.
    
    Args:
        data_path (str): Path to normalized data CSV
        output_dir (str): Directory to save visualizations
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    data = pd.read_csv(data_path)
    
    # Convert date column to datetime
    data["EventDateUTC"] = pd.to_datetime(data["EventDateUTC"])
    
    # Group by date and competitor, count mentions
    time_series = data.groupby([pd.Grouper(key="EventDateUTC", freq="D"), "competitor_canonical"]).size().reset_index(name="count")
    
    # Create plot
    plt.figure(figsize=(16, 10))
    
    # Get top 5 competitors by mention count
    top_competitors = data["competitor_canonical"].value_counts().nlargest(5).index.tolist()
    
    # Plot each competitor as a line
    for competitor in top_competitors:
        competitor_data = time_series[time_series["competitor_canonical"] == competitor]
        sns.lineplot(data=competitor_data, x="EventDateUTC", y="count", label=competitor, linewidth=2.5)
    
    # Customize plot
    plt.title("Competitor Mentions Over Time", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Number of Mentions", fontsize=14)
    plt.legend(title="Competitor", title_fontsize=13, fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Save plot
    output_path = os.path.join(output_dir, "competitor_timeline.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved competitor timeline chart to {output_path}")
    
    return output_path

def create_variant_analysis_chart(data_path, config_path, output_dir="visualizations"):
    """
    Create a chart showing distribution of variant mentions for each competitor.
    
    Args:
        data_path (str): Path to normalized data CSV
        config_path (str): Path to competitor normalization config JSON
        output_dir (str): Directory to save visualizations
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data and config
    data = pd.read_csv(data_path)
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Count variant mentions
    variant_counts = data["variant_found"].value_counts().to_dict()
    
    # Create a mapping from variant to canonical name
    variant_to_canonical = {}
    for canonical, variants in config.items():
        for variant in variants:
            variant_to_canonical[variant] = canonical
    
    # Group variants by canonical name
    canonical_to_variants = {}
    for variant, count in variant_counts.items():
        if variant in variant_to_canonical:
            canonical = variant_to_canonical[variant]
            if canonical not in canonical_to_variants:
                canonical_to_variants[canonical] = []
            canonical_to_variants[canonical].append((variant, count))
    
    # Get top competitors by mention count
    top_competitors = list(data["competitor_canonical"].value_counts().nlargest(5).index)
    
    # Create plot for each top competitor
    for competitor in top_competitors:
        if competitor in canonical_to_variants:
            variants = canonical_to_variants[competitor]
            variants.sort(key=lambda x: x[1], reverse=True)
            
            # Extract data for plotting
            variant_names = [v[0] for v in variants]
            variant_counts = [v[1] for v in variants]
            
            plt.figure(figsize=(14, 8))
            ax = sns.barplot(x=variant_names, y=variant_counts)
            
            # Customize plot
            plt.title(f"Variants of '{competitor}' Mentioned in Calls", fontsize=16)
            plt.xlabel("Variant", fontsize=14)
            plt.ylabel("Number of Mentions", fontsize=14)
            plt.xticks(rotation=45, ha="right")
            
            # Add value labels on bars
            for i, v in enumerate(variant_counts):
                ax.text(i, v + 1, str(v), ha='center', fontsize=12)
            
            plt.tight_layout()
            
            # Save plot
            output_path = os.path.join(output_dir, f"{competitor.replace(' ', '_')}_variants.png")
            plt.savefig(output_path, dpi=300)
            print(f"Saved variant analysis chart for {competitor} to {output_path}")
    
    return output_dir

def generate_analysis_dashboard(data_path, config_path, output_dir="visualizations"):
    """
    Generate a comprehensive set of visualizations for competitor analysis.
    
    Args:
        data_path (str): Path to normalized data CSV
        config_path (str): Path to competitor normalization config JSON
        output_dir (str): Directory to save visualizations
    
    Returns:
        str: Path to the output directory with visualizations
    """
    # Configure plot style
    setup_plotting_style()
    
    # Create timestamp for this analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dashboard_dir = f"{output_dir}_{timestamp}"
    os.makedirs(dashboard_dir, exist_ok=True)
    
    print(f"Generating competitor analysis dashboard in {dashboard_dir}...")
    
    # Generate visualizations
    create_competitor_frequency_chart(data_path, dashboard_dir)
    create_competitor_timeline(data_path, dashboard_dir)
    create_variant_analysis_chart(data_path, config_path, dashboard_dir)
    
    # Create dashboard HTML file
    create_html_dashboard(dashboard_dir)
    
    print(f"Analysis dashboard completed: {dashboard_dir}/dashboard.html")
    return dashboard_dir

def create_html_dashboard(dashboard_dir):
    """
    Create an HTML dashboard that displays all visualizations.
    
    Args:
        dashboard_dir (str): Directory with visualization files
    """
    # Get all PNG files in the dashboard directory
    visualization_files = [f for f in os.listdir(dashboard_dir) if f.endswith('.png')]
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Competitor Analysis Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1 {{
                color: #333;
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 1px solid #ddd;
            }}
            .dashboard {{
                display: flex;
                flex-direction: column;
                gap: 30px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            .visualization {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }}
            .visualization img {{
                width: 100%;
                height: auto;
            }}
            .title {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #444;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                color: #777;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <h1>Competitor Analysis Dashboard</h1>
        <p style="text-align: center;">Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
        
        <div class="dashboard">
    """
    
    # Add each visualization to the dashboard
    for image_file in visualization_files:
        # Create a human-readable title from the filename
        title = image_file.replace('_', ' ').replace('.png', '')
        title = ' '.join(word.capitalize() for word in title.split())
        
        html_content += f"""
            <div class="visualization">
                <div class="title">{title}</div>
                <img src="{image_file}" alt="{title}" />
            </div>
        """
    
    # Close the HTML
    html_content += """
        </div>
        
        <div class="footer">
            <p>This dashboard was automatically generated by the Fabric Competitor Analysis Agent</p>
        </div>
    </body>
    </html>
    """
    
    # Write the HTML file
    with open(os.path.join(dashboard_dir, 'dashboard.html'), 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    # Example usage
    data_path = "source_normalized.csv"
    config_path = "competitor_normalization.json"
    
    # Generate dashboard
    generate_analysis_dashboard(data_path, config_path)