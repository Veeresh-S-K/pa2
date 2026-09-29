import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

traces = ['Trace1', 'Trace2', 'Trace3']
prefetchers = ['no', 'ip', 'spp']

data = []

for t_idx, trace in enumerate(traces):
    for pref in prefetchers:
        filename = f"{pref}_trace{t_idx+1}"
        if not os.path.exists(filename):
            print(f"Warning: {filename} not found.")
            continue
            
        with open(filename, 'r') as f:
            content = f.read()
            
        # Parse IPC
        ipc_match = re.search(r'CPU 0 cumulative IPC:\s*([\d\.]+)', content)
        ipc = float(ipc_match.group(1)) if ipc_match else 0
        
        # Parse L1D Load Misses and MPKI
        l1d_match = re.search(r'L1D LOAD\s+ACCESS:\s+\d+\s+HIT:\s+\d+\s+MISS:\s+(\d+).*?MPKI:\s+([\d\.]+)', content)
        l1d_miss = int(l1d_match.group(1)) if l1d_match else 0
        l1d_mpki = float(l1d_match.group(2)) if l1d_match else 0
        
        # Parse Prefetch Stats (Useful, Issued, Accuracy)
        pref_match = re.search(r'L1D USEFUL LOAD PREFETCHES:\s+(\d+)\s+PREFETCH ISSUED TO LOWER LEVEL:\s+(\d+).*?ACCURACY:\s+([\d\.]+)', content)
        if pref_match:
            useful_pref = int(pref_match.group(1))
            issued_pref = int(pref_match.group(2))
            accuracy = float(pref_match.group(3)) if pref_match.group(3) != '-nan' else 0
        else:
            pref_nan_match = re.search(r'L1D USEFUL LOAD PREFETCHES:\s+(\d+)\s+PREFETCH ISSUED TO LOWER LEVEL:\s+(\d+).*?ACCURACY:\s+-nan', content)
            if pref_nan_match:
                useful_pref = int(pref_nan_match.group(1))
                issued_pref = int(pref_nan_match.group(2))
                accuracy = 0.0
            else:
                useful_pref = 0
                issued_pref = 0
                accuracy = 0.0
                
        data.append({
            'Trace': trace,
            'Prefetcher': pref,
            'IPC': ipc,
            'L1D_Load_Misses': l1d_miss,
            'L1D_MPKI': l1d_mpki,
            'Useful_Prefetches': useful_pref,
            'Issued_Prefetches': issued_pref,
            'Accuracy': accuracy
        })

df = pd.DataFrame(data)
if df.empty:
    print("No data loaded yet.")
else:
    df_no = df[df['Prefetcher'] == 'no'].set_index('Trace') if 'no' in df['Prefetcher'].values else pd.DataFrame()
    df_ip = df[df['Prefetcher'] == 'ip'].set_index('Trace') if 'ip' in df['Prefetcher'].values else pd.DataFrame()
    df_spp = df[df['Prefetcher'] == 'spp'].set_index('Trace') if 'spp' in df['Prefetcher'].values else pd.DataFrame()
    
    results = pd.DataFrame(index=df['Trace'].unique())
    
    if not df_no.empty:
        results['Base_IPC'] = df_no['IPC']
        results['Base_Misses'] = df_no['L1D_Load_Misses']
    
    if not df_ip.empty:
        results['IP_IPC'] = df_ip['IPC']
        results['IP_Misses'] = df_ip['L1D_Load_Misses']
        results['IP_Issued'] = df_ip['Issued_Prefetches']
        results['IP_Useful'] = df_ip['Useful_Prefetches']
        results['IP_Accuracy'] = df_ip['Accuracy']
        
    if not df_spp.empty:
        results['SPP_IPC'] = df_spp['IPC']
        results['SPP_Misses'] = df_spp['L1D_Load_Misses']
        results['SPP_Issued'] = df_spp['Issued_Prefetches']
        results['SPP_Useful'] = df_spp['Useful_Prefetches']
        results['SPP_Accuracy'] = df_spp['Accuracy']

    print("\n=== RAW METRICS TABULAR RESULTS ===")
    pd.set_option('display.max_columns', None)
    print(results.to_string())

    # Plotting
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    x = np.arange(len(results.index))
    width = 0.25

    # 1. IPC
    ax = axes[0, 0]
    if not df_no.empty: ax.bar(x - width, results['Base_IPC'], width, label='Baseline', color='gray')
    if not df_ip.empty: ax.bar(x, results['IP_IPC'], width, label='IP Prefetcher', color='royalblue')
    if not df_spp.empty: ax.bar(x + width, results['SPP_IPC'], width, label='SPP Prefetcher', color='tomato')
    ax.set_ylabel('IPC')
    ax.set_title('IPC Comparison')
    ax.set_xticks(x); ax.set_xticklabels(results.index)
    ax.legend()

    # 2. Raw Misses
    ax = axes[0, 1]
    if not df_no.empty: ax.bar(x - width, results['Base_Misses'], width, label='Baseline Misses', color='gray')
    if not df_ip.empty: ax.bar(x, results['IP_Misses'], width, label='IP Misses', color='royalblue')
    if not df_spp.empty: ax.bar(x + width, results['SPP_Misses'], width, label='SPP Misses', color='tomato')
    ax.set_ylabel('Total L1D Load Misses')
    ax.set_title('Raw L1D Misses Comparison')
    ax.set_xticks(x); ax.set_xticklabels(results.index)
    ax.legend()

    # 3. Accuracy 
    ax = axes[1, 0]
    width_acc = 0.35
    if not df_ip.empty: ax.bar(x - width_acc/2, results['IP_Accuracy'], width_acc, label='IP Accuracy', color='mediumseagreen')
    if not df_spp.empty: ax.bar(x + width_acc/2, results['SPP_Accuracy'], width_acc, label='SPP Accuracy', color='darkgreen')
    ax.set_ylabel('Percentage (%)')
    ax.set_title('Prefetcher Accuracy')
    ax.set_xticks(x); ax.set_xticklabels(results.index)
    ax.legend()

    # 4. Total Prefetches Issued (Cache Pollution Indicator)
    ax = axes[1, 1]
    if not df_ip.empty: ax.bar(x - width_acc/2, results['IP_Issued'], width_acc, label='IP Issued Prefetches', color='orchid')
    if not df_spp.empty: ax.bar(x + width_acc/2, results['SPP_Issued'], width_acc, label='SPP Issued Prefetches', color='purple')
    ax.set_ylabel('Total Prefetches Issued to Lower Level')
    ax.set_title('Raw Prefetcher Aggressiveness (Issued Prefetches)')
    ax.set_xticks(x); ax.set_xticklabels(results.index)
    ax.legend()

    plt.tight_layout()
    plt.savefig('Analysis_Plots.png')
    print("\n--> 4 Plots successfully saved to Analysis_Plots.png")
