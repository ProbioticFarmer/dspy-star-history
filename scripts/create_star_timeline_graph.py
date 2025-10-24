#!/usr/bin/env python3
"""
Create timeline visualization of DSPy stars: Real vs Fake
With critical dates and events marked
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import numpy as np

class StarTimelineVisualizer:
    """Create comprehensive timeline visualization."""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "github"
        self.enriched_file = self.data_dir / "full_forensic_enriched_data.jsonl"

        # Load collected data
        print("Loading collected enriched data...")
        self.accounts = []
        with open(self.enriched_file, 'r') as f:
            for line in f:
                self.accounts.append(json.loads(line))

        print(f"Loaded {len(self.accounts)} accounts")
        print(f"Date range: {self.accounts[0]['starred_at'][:10]} to {self.accounts[-1]['starred_at'][:10]}\n")

    def apply_advanced_detection(self):
        """Apply full CMU detection to classify stars."""
        print("Applying advanced CMU detection...")

        # Basic suspicious
        basic_fake_usernames = set()
        for acc in self.accounts:
            if acc.get('is_suspicious') or acc.get('status') == 'deleted':
                basic_fake_usernames.add(acc['username'])

        # Temporal clustering
        print("  - Temporal clustering analysis...")
        temporal_fake = self.detect_temporal_clustering()

        # Dormant accounts
        print("  - Dormant account analysis...")
        dormant_fake = self.detect_dormant_accounts()

        # Low activity
        print("  - Activity diversity analysis...")
        low_activity_fake = self.detect_low_activity()

        # Combine all
        all_fake_usernames = basic_fake_usernames | temporal_fake | dormant_fake | low_activity_fake

        print(f"\nDetection results:")
        print(f"  - Basic fake: {len(basic_fake_usernames)}")
        print(f"  - Temporal clustering: {len(temporal_fake)}")
        print(f"  - Dormant accounts: {len(dormant_fake)}")
        print(f"  - Low activity: {len(low_activity_fake)}")
        print(f"  - Total fake (CMU): {len(all_fake_usernames)}")
        print(f"  - Fake percentage: {len(all_fake_usernames)/len(self.accounts)*100:.1f}%\n")

        return all_fake_usernames

    def detect_temporal_clustering(self, threshold_minutes=60):
        """Detect temporal clustering."""
        timestamps = []
        for acc in self.accounts:
            if not acc.get('is_suspicious') and acc.get('status') != 'deleted':
                ts = datetime.fromisoformat(acc['starred_at'].replace('Z', '+00:00'))
                timestamps.append((acc['username'], ts))

        timestamps.sort(key=lambda x: x[1])

        suspicious = set()
        if timestamps:
            current_cluster = [timestamps[0]]
            for username, ts in timestamps[1:]:
                last_ts = current_cluster[-1][1]
                diff_minutes = (ts - last_ts).total_seconds() / 60

                if diff_minutes <= threshold_minutes:
                    current_cluster.append((username, ts))
                else:
                    if len(current_cluster) >= 10:
                        for u, _ in current_cluster:
                            suspicious.add(u)
                    current_cluster = [(username, ts)]

            if len(current_cluster) >= 10:
                for u, _ in current_cluster:
                    suspicious.add(u)

        return suspicious

    def detect_dormant_accounts(self):
        """Detect dormant accounts."""
        suspicious = set()
        for acc in self.accounts:
            if acc.get('status') == 'deleted' or acc.get('is_suspicious'):
                continue

            created = datetime.fromisoformat(acc['account_created'].replace('Z', '+00:00'))
            starred = datetime.fromisoformat(acc['starred_at'].replace('Z', '+00:00'))
            account_age_days = (starred - created).days

            if account_age_days > 365 and acc.get('public_repos', 0) < 3:
                suspicious.add(acc['username'])

        return suspicious

    def detect_low_activity(self):
        """Detect low activity accounts."""
        suspicious = set()
        for acc in self.accounts:
            if acc.get('status') == 'deleted' or acc.get('is_suspicious'):
                continue

            repos = acc.get('public_repos', 0)
            followers = acc.get('followers', 0)
            following = acc.get('following', 0)

            if repos == 0 and followers < 5 and following < 10:
                suspicious.add(acc['username'])

        return suspicious

    def create_timeline_graph(self, fake_usernames):
        """Create the main timeline visualization."""
        print("Creating timeline visualization...")

        # Group by day
        daily_real = defaultdict(int)
        daily_fake = defaultdict(int)

        for acc in self.accounts:
            date = datetime.fromisoformat(acc['starred_at'].replace('Z', '+00:00')).date()
            if acc['username'] in fake_usernames:
                daily_fake[date] += 1
            else:
                daily_real[date] += 1

        # Get all dates
        all_dates = sorted(set(list(daily_real.keys()) + list(daily_fake.keys())))

        # Create cumulative data for smooth lines
        dates = []
        real_counts = []
        fake_counts = []

        for date in all_dates:
            dates.append(date)
            real_counts.append(daily_real[date])
            fake_counts.append(daily_fake[date])

        # Create figure
        fig, ax = plt.subplots(figsize=(20, 10))

        # Plot real and fake stars
        ax.plot(dates, real_counts, color='green', linewidth=2, label='Real Stars', alpha=0.8)
        ax.plot(dates, fake_counts, color='red', linewidth=2, label='Fake Stars (CMU Detection)', alpha=0.8)

        # Critical dates
        critical_dates = {
            # Academic milestones
            datetime(2019, 9, 1).date(): ('PhD begins\nwith Matei', 'bottom', 'blue'),
            datetime(2022, 12, 1).date(): ('First DSP\npaper', 'bottom', 'blue'),
            datetime(2023, 8, 14).date(): ('DSP→DSPy\nrebrand', 'bottom', 'purple'),
            datetime(2023, 10, 5).date(): ('DSPy paper\npublished', 'top', 'blue'),
            datetime(2024, 1, 15).date(): ('ICLR 2024\nSpotlight', 'top', 'blue'),
            datetime(2024, 8, 1).date(): ('Omar→\nDatabricks', 'bottom', 'orange'),

            # Funding events
            datetime(2023, 9, 14).date(): ('$43B valuation\n$500M raise\nSpike ENDS', 'top', 'darkred'),
            datetime(2024, 12, 17).date(): ('$62B valuation\n$10B raise', 'top', 'darkred'),

            # Spike markers
            datetime(2023, 8, 24).date(): ('SPIKE\nBEGINS', 'bottom', 'darkred'),
            datetime(2023, 9, 7).date(): ('Peak spike\n223 stars\nz=21.75', 'top', 'darkred'),
        }

        # Add vertical lines for critical dates
        for date, (label, position, color) in critical_dates.items():
            if date >= min(dates) and date <= max(dates):
                ax.axvline(x=date, color=color, linestyle='--', alpha=0.5, linewidth=1.5)

                # Position label
                y_pos = ax.get_ylim()[1] * 0.95 if position == 'top' else ax.get_ylim()[1] * 0.05
                ax.text(date, y_pos, label,
                       rotation=90, verticalalignment='top' if position == 'top' else 'bottom',
                       fontsize=9, color=color, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

        # Shade the spike period (Aug 24 - Sep 14, 2023)
        spike_start = datetime(2023, 8, 24).date()
        spike_end = datetime(2023, 9, 14).date()
        if spike_start >= min(dates) and spike_end <= max(dates):
            ax.axvspan(spike_start, spike_end, alpha=0.2, color='red',
                      label='Spike Period (22 days)')

        # Calculate and show baselines
        pre_spike_dates = [d for d in dates if d < spike_start]
        if pre_spike_dates:
            pre_spike_avg_real = np.mean([daily_real[d] for d in pre_spike_dates])
            pre_spike_avg_fake = np.mean([daily_fake[d] for d in pre_spike_dates])
            ax.axhline(y=pre_spike_avg_real, color='green', linestyle=':',
                      alpha=0.5, linewidth=1, label=f'Pre-spike avg real: {pre_spike_avg_real:.1f}/day')
            ax.axhline(y=pre_spike_avg_fake, color='red', linestyle=':',
                      alpha=0.5, linewidth=1, label=f'Pre-spike avg fake: {pre_spike_avg_fake:.1f}/day')

        # Formatting
        ax.set_xlabel('Date', fontsize=14, fontweight='bold')
        ax.set_ylabel('Stars per Day', fontsize=14, fontweight='bold')
        ax.set_title('DSPy GitHub Stars: Real vs Fake Over Time\nFull CMU Detection (Temporal Clustering + Dormant Accounts + Activity Analysis)',
                    fontsize=16, fontweight='bold', pad=20)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=45, ha='right')

        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')

        # Legend
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

        # Tight layout
        plt.tight_layout()

        # Save
        output_file = self.data_dir.parent.parent / 'dspy_stars_timeline.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\nGraph saved to: {output_file}")

        # Also save high-res version
        output_file_hires = self.data_dir.parent.parent / 'dspy_stars_timeline_hires.png'
        plt.savefig(output_file_hires, dpi=600, bbox_inches='tight')
        print(f"High-res version saved to: {output_file_hires}")

        plt.close()

        # Create summary statistics
        self.create_summary_stats(dates, daily_real, daily_fake, spike_start, spike_end)

    def create_summary_stats(self, dates, daily_real, daily_fake, spike_start, spike_end):
        """Create summary statistics."""

        # Pre-spike period
        pre_spike = [d for d in dates if d < spike_start]
        pre_real = sum(daily_real[d] for d in pre_spike)
        pre_fake = sum(daily_fake[d] for d in pre_spike)
        pre_total = pre_real + pre_fake

        # Spike period
        spike_dates = [d for d in dates if spike_start <= d <= spike_end]
        spike_real = sum(daily_real[d] for d in spike_dates)
        spike_fake = sum(daily_fake[d] for d in spike_dates)
        spike_total = spike_real + spike_fake

        # Post-spike
        post_spike = [d for d in dates if d > spike_end]
        post_real = sum(daily_real[d] for d in post_spike)
        post_fake = sum(daily_fake[d] for d in post_spike)
        post_total = post_real + post_fake

        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)

        print(f"\nPRE-SPIKE PERIOD (before {spike_start}):")
        print(f"  Duration: {len(pre_spike)} days")
        print(f"  Total stars: {pre_total}")
        print(f"  Real: {pre_real} ({pre_real/pre_total*100:.1f}%)")
        print(f"  Fake: {pre_fake} ({pre_fake/pre_total*100:.1f}%)")
        print(f"  Avg/day: {pre_total/len(pre_spike):.1f}")

        print(f"\nSPIKE PERIOD ({spike_start} to {spike_end}):")
        print(f"  Duration: {len(spike_dates)} days")
        print(f"  Total stars: {spike_total}")
        print(f"  Real: {spike_real} ({spike_real/spike_total*100:.1f}%)")
        print(f"  Fake: {spike_fake} ({spike_fake/spike_total*100:.1f}%)")
        print(f"  Avg/day: {spike_total/len(spike_dates):.1f}")
        print(f"  Velocity increase: {(spike_total/len(spike_dates)) / (pre_total/len(pre_spike)):.1f}x")

        print(f"\nPOST-SPIKE PERIOD (after {spike_end}):")
        print(f"  Duration: {len(post_spike)} days")
        print(f"  Total stars: {post_total}")
        print(f"  Real: {post_real} ({post_real/post_total*100:.1f}%)")
        print(f"  Fake: {post_fake} ({post_fake/post_total*100:.1f}%)")
        print(f"  Avg/day: {post_total/len(post_spike):.1f}")


def main():
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║       DSPy Star Timeline Visualization                            ║
║       Real vs Fake Stars with Critical Events                     ║
╚════════════════════════════════════════════════════════════════════╝
""")

    viz = StarTimelineVisualizer()
    fake_usernames = viz.apply_advanced_detection()
    viz.create_timeline_graph(fake_usernames)

    print("\n✅ Visualization complete!")


if __name__ == "__main__":
    main()
