#!/usr/bin/env python3
"""
回测结果可视化脚本
使用 matplotlib 绘制回测结果图表
"""
import json
import zipfile
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_backtest_results(result_path):
    """加载回测结果"""
    if result_path.endswith('.zip'):
        with zipfile.ZipFile(result_path, 'r') as zip_ref:
            # 查找 JSON 文件
            json_files = [f for f in zip_ref.namelist() if f.endswith('.json') and 'config' not in f]
            if not json_files:
                raise ValueError("未找到回测结果 JSON 文件")
            
            # 读取第一个匹配的 JSON 文件
            with zip_ref.open(json_files[0]) as f:
                data = json.load(f)
                return data
    else:
        with open(result_path, 'r') as f:
            data = json.load(f)
            return data

def create_profit_chart(df_trades, output_dir):
    """创建利润曲线图"""
    if df_trades.empty:
        print("没有交易数据")
        return
    
    # 转换时间
    df_trades['close_date'] = pd.to_datetime(df_trades['close_date'])
    df_trades = df_trades.sort_values('close_date')
    
    # 计算累计利润
    df_trades['cumulative_profit'] = df_trades['profit_abs'].cumsum()
    df_trades['cumulative_profit_pct'] = (df_trades['profit_ratio'] * 100).cumsum()
    
    # 创建图表
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
    
    # 图1: 累计利润 (USDT)
    ax1.plot(df_trades['close_date'], df_trades['cumulative_profit'], 
             linewidth=2, color='#2E86AB', label='累计利润')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('累计利润曲线 (USDT)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('利润 (USDT)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 图2: 每笔交易盈亏
    colors = ['green' if x > 0 else 'red' for x in df_trades['profit_abs']]
    ax2.bar(df_trades['close_date'], df_trades['profit_abs'], 
            color=colors, alpha=0.6, width=0.5)
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax2.set_title('单笔交易盈亏分布', fontsize=14, fontweight='bold')
    ax2.set_ylabel('盈亏 (USDT)', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 图3: 累计胜率
    df_trades['is_win'] = df_trades['profit_abs'] > 0
    df_trades['win_count'] = df_trades['is_win'].cumsum()
    df_trades['win_rate'] = (df_trades['win_count'] / (df_trades.index + 1)) * 100
    
    ax3.plot(df_trades['close_date'], df_trades['win_rate'], 
             linewidth=2, color='#A23B72', label='累计胜率')
    ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax3.set_title('胜率变化趋势', fontsize=14, fontweight='bold')
    ax3.set_ylabel('胜率 (%)', fontsize=12)
    ax3.set_xlabel('日期', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_ylim(0, 100)
    
    # 格式化 x 轴日期
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 保存图表
    output_file = output_dir / 'profit_chart.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ 利润图表已保存: {output_file}")
    
    plt.close()

def create_stats_chart(df_trades, output_dir):
    """创建统计图表"""
    if df_trades.empty:
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # 图1: 盈亏分布直方图
    profits = df_trades['profit_ratio'] * 100
    ax1.hist(profits, bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax1.axvline(x=profits.mean(), color='red', linestyle='--', 
                linewidth=2, label=f'平均: {profits.mean():.2f}%')
    ax1.set_title('盈亏比例分布', fontsize=12, fontweight='bold')
    ax1.set_xlabel('盈亏比例 (%)', fontsize=10)
    ax1.set_ylabel('交易次数', fontsize=10)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 图2: 做多 vs 做空表现
    long_trades = df_trades[df_trades['is_short'] == False]
    short_trades = df_trades[df_trades['is_short'] == True]
    
    categories = ['做多', '做空']
    profits_sum = [
        long_trades['profit_abs'].sum() if not long_trades.empty else 0,
        short_trades['profit_abs'].sum() if not short_trades.empty else 0
    ]
    colors_bar = ['green' if x > 0 else 'red' for x in profits_sum]
    
    bars = ax2.bar(categories, profits_sum, color=colors_bar, alpha=0.7, edgecolor='black')
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax2.set_title('多空盈亏对比', fontsize=12, fontweight='bold')
    ax2.set_ylabel('总盈亏 (USDT)', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 在柱状图上添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom' if height > 0 else 'top', fontsize=10)
    
    # 图3: 持仓时长分布
    df_trades['duration_hours'] = (
        pd.to_datetime(df_trades['close_date']) - 
        pd.to_datetime(df_trades['open_date'])
    ).dt.total_seconds() / 3600
    
    ax3.hist(df_trades['duration_hours'], bins=30, color='#F18F01', 
             alpha=0.7, edgecolor='black')
    ax3.axvline(x=df_trades['duration_hours'].mean(), color='red', 
                linestyle='--', linewidth=2, 
                label=f'平均: {df_trades["duration_hours"].mean():.1f}h')
    ax3.set_title('持仓时长分布', fontsize=12, fontweight='bold')
    ax3.set_xlabel('持仓时长 (小时)', fontsize=10)
    ax3.set_ylabel('交易次数', fontsize=10)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 图4: 出场原因统计
    exit_reasons = df_trades['exit_reason'].value_counts()
    colors_pie = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    wedges, texts, autotexts = ax4.pie(exit_reasons.values, 
                                         labels=exit_reasons.index,
                                         autopct='%1.1f%%',
                                         colors=colors_pie[:len(exit_reasons)],
                                         startangle=90)
    ax4.set_title('出场原因分布', fontsize=12, fontweight='bold')
    
    # 美化百分比文字
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')
    
    plt.tight_layout()
    
    # 保存图表
    output_file = output_dir / 'stats_chart.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ 统计图表已保存: {output_file}")
    
    plt.close()

def main():
    # 查找最新的回测结果
    script_dir = Path(__file__).parent
    backtest_dir = script_dir / 'backtest_results'
    result_files = list(backtest_dir.glob('backtest-result-*.zip'))
    
    if not result_files:
        print("❌ 未找到回测结果文件")
        sys.exit(1)
    
    # 使用最新的结果文件
    latest_result = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"📊 加载回测结果: {latest_result.name}")
    
    # 加载数据
    result_data = load_backtest_results(str(latest_result))
    
    # 处理策略数据
    if 'strategy' in result_data:
        # 新格式
        strategy_data = result_data['strategy']
        strategy_name = list(strategy_data.keys())[0]
        trades_list = strategy_data[strategy_name]['trades']
    elif isinstance(result_data, dict) and any(k for k in result_data.keys() if 'Strategy' in k):
        # 旧格式 - 直接包含策略名
        strategy_name = [k for k in result_data.keys() if 'Strategy' in k][0]
        trades_list = result_data[strategy_name]['trades'] if 'trades' in result_data[strategy_name] else result_data[strategy_name]
    else:
        trades_list = result_data
    
    if not trades_list:
        print("❌ 没有交易数据")
        sys.exit(1)
    
    df_trades = pd.DataFrame(trades_list)
    print(f"✓ 加载了 {len(df_trades)} 笔交易")
    
    # 创建输出目录
    output_dir = backtest_dir
    
    # 生成图表
    print("\n生成可视化图表...")
    create_profit_chart(df_trades, output_dir)
    create_stats_chart(df_trades, output_dir)
    
    print(f"\n✅ 所有图表已生成在: {output_dir}")
    print(f"   - profit_chart.png (利润曲线)")
    print(f"   - stats_chart.png (统计分析)")

if __name__ == '__main__':
    main()
