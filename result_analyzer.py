import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def load_query_logs(log_dir):
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".json")]
    data_frames = [pd.read_json(file).assign(query_component=os.path.basename(file).replace('.json', '')) for file in log_files]
    return pd.concat(data_frames, ignore_index=True) if data_frames else pd.DataFrame()

def process_query_logs(df):
    df['request_timestamp_ms'] = df['request_timestamp_ms'].astype(float)
    df['respond_timestamp_ms'] = df['respond_timestamp_ms'].astype(float)
    df['latency_ms'] = df['respond_timestamp_ms'] - df['request_timestamp_ms']
    df['timestamp'] = pd.to_datetime(df['request_timestamp_ms'], unit='ms')
    df['query'] = df['query'].str.replace(r'\s+', ' ', regex=True)
    return df[['timestamp', 'latency_ms', 'query_component', 'status_code', 'query']]

def compute_statistics(df):
    df_success = df[df['status_code'] == 200]
    summary = df_success['latency_ms'].agg(
        ['count', 'mean', 'std', 'min', 'median', 'max']
    ).to_dict()
    summary['quantile_99'] = df_success['latency_ms'].quantile(0.99)
    summary['quantile_95'] = df_success['latency_ms'].quantile(0.95)
    summary['quantile_75'] = df_success['latency_ms'].quantile(0.75)
    summary['success_rate'] = (df[df['status_code'] == 200].shape[0] / df.shape[0]) * 100
    return summary

def plot_latency_over_time(df, output_dir, experiment_duration):
    os.makedirs(output_dir, exist_ok=True)
    df_success = df[df['status_code'] == 200]

    if experiment_duration <= 300:
        window = '5s'
    elif experiment_duration <= 1800 and experiment_duration > 300:
        window = '30s'
    else:
        window = '1min'

    for component, df_component in df_success.groupby('query_component'):
        plt.figure(figsize=(12, 6))
        df_component = df_component.set_index('timestamp')[['latency_ms']].resample(window).mean().reset_index()
        sns.lineplot(x='timestamp', y='latency_ms', data=df_component, label=component)
        plt.xlabel('Time')
        plt.ylabel('Latency (ms)')
        plt.title(f'Query Latency Over Time ({component})')
        plt.xticks(rotation=45)
        plt.legend(title='Query Component')
        plt.savefig(os.path.join(output_dir, f'latency_over_time_{component}.png'))
        plt.close()

    plt.figure(figsize=(12, 6))
    df_resampled = df.set_index('timestamp')[['latency_ms']].resample(window).mean().reset_index()
    sns.lineplot(x='timestamp', y='latency_ms', data=df_resampled, alpha=0.7)
    plt.xlabel('Time')
    plt.ylabel('Latency (ms)')
    plt.title('Aggregated Query Latency Over Time (success and failed queries)')
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(output_dir, 'latency_over_time_aggregated.png'))
    plt.close()

    plt.figure(figsize=(12, 6))
    df_resampled = df_success.set_index('timestamp')[['latency_ms']].resample(window).mean().reset_index()
    sns.lineplot(x='timestamp', y='latency_ms', data=df_resampled, alpha=0.7)
    plt.xlabel('Time')
    plt.ylabel('Latency (ms)')
    plt.title('Aggregated Query Latency Over Time (only successful queries)')
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(output_dir, 'latency_over_time_aggregated_success.png'))
    plt.close()

    plt.figure(figsize=(12, 6))
    for component, df_component in df_success.groupby('query_component'):
        df_component = df_component.set_index('timestamp')[['latency_ms']].resample(window).mean().reset_index()
        sns.lineplot(x='timestamp', y='latency_ms', data=df_component, label=component)
    plt.xlabel('Time')
    plt.ylabel('Latency (ms)')
    plt.title('Query Latency Over Time (All Components)')
    plt.xticks(rotation=45)
    plt.legend(title='Query Component')
    plt.savefig(os.path.join(output_dir, 'latency_over_time_all_components.png'))
    plt.close()

def plot_latency_distribution(df, output_dir):
    df_success = df[df['status_code'] == 200]
    plt.figure(figsize=(8, 5))
    sns.histplot(df_success['latency_ms'], bins=50, kde=True)
    plt.xlabel('Latency (ms)')
    plt.ylabel('Frequency')
    plt.title('Latency Distribution')
    plt.savefig(os.path.join(output_dir, 'latency_distribution.png'))
    plt.close()

def plot_latency_boxplot(df, output_dir):
    df_success = df[df['status_code'] == 200]
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='query_component', y='latency_ms', data=df)
    plt.xlabel('Query Component', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency Comparison Across Query Components', fontsize=14)
    plt.savefig(os.path.join(output_dir, 'latency_boxplot.png'))
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.boxplot(y=df_success['latency_ms'])
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Overall Latency Distribution', fontsize=14)
    plt.savefig(os.path.join(output_dir, 'latency_boxplot_overall.png'))
    plt.close()

    plt.figure(figsize=(14, 8))
    sns.boxplot(x='query', y='latency_ms', data=df_success)
    plt.xlabel('Query', fontsize=12)
    plt.xticks(rotation=5)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency Comparison Across Queries', fontsize=14)
    plt.savefig(os.path.join(output_dir, 'latency_boxplot_queries.png'))
    plt.close()

def analyze_query_logs(log_dir, output_dir, experiment_duration):
    df = load_query_logs(log_dir)
    if df.empty:
        print("No valid data found.")
        return
    df = process_query_logs(df)

    # Compute statistics for each query component
    stats_per_component = df.groupby('query_component', group_keys=False).apply(compute_statistics).to_dict()
    stats_per_query = df.groupby('query', group_keys=False).apply(compute_statistics).to_dict()
    overall_stats = compute_statistics(df)

    print("Overall Latency Statistics:")
    print(overall_stats)

    os.makedirs(output_dir, exist_ok=True)

    # Save statistics to JSON
    with open(os.path.join(output_dir, 'query_stats.json'), 'w') as f:
        json.dump({"per_component": stats_per_component, "per_query": stats_per_query, "overall": overall_stats}, f, indent=4)

    # Generate plots
    plot_latency_over_time(df, output_dir, experiment_duration)
    plot_latency_distribution(df, output_dir)
    plot_latency_boxplot(df, output_dir)

    print(f"Analysis complete. Results saved in {output_dir}")

def analyze_raw_data_get_results(log_path, experiment_duration):
    query_logs_dir = f"{log_path}/query_component_logs"
    output_dir = f"{log_path}/analysis_result"
    analyze_query_logs(query_logs_dir, output_dir, experiment_duration)

### for testing
if __name__ == "__main__":
    log_path = "logs/experiment_p1_me2-small_lg2x500_qc2x400/1738707106"
    analyze_raw_data_get_results(log_path, 600)