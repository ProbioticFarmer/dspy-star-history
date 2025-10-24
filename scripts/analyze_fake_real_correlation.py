#!/usr/bin/env python3
"""
Analyze correlation between real star decline and fake star increase
Test hypothesis: Fake stars automatically bought when real stars drop
"""

import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from scipy import stats

class CorrelationAnalyzer:
    """Analyze inverse correlation between real and fake stars."""

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

    def apply_full_detection(self):
        """Apply full CMU detection."""
        print("Applying full CMU detection...")

        # Basic fake
        basic_fake = set()
        for acc in self.accounts:
            if acc.get('is_suspicious') or acc.get('status') == 'deleted':
                basic_fake.add(acc['username'])

        # Temporal clustering
        temporal_fake = self.detect_temporal_clustering()

        # Dormant accounts
        dormant_fake = self.detect_dormant_accounts()

        # Low activity
        low_activity = self.detect_low_activity()

        # Combine
        all_fake = basic_fake | temporal_fake | dormant_fake | low_activity

        print(f"Total fake accounts: {len(all_fake)} ({len(all_fake)/len(self.accounts)*100:.1f}%)\n")

        return all_fake

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

    def analyze_weekly_correlation(self, fake_usernames):
        """Analyze weekly patterns to detect inverse correlation."""
        print(f"{'='*80}")
        print("WEEKLY CORRELATION ANALYSIS")
        print(f"{'='*80}\n")

        # Group by week
        weekly_real = defaultdict(int)
        weekly_fake = defaultdict(int)

        for acc in self.accounts:
            date = datetime.fromisoformat(acc['starred_at'].replace('Z', '+00:00')).date()
            # Get ISO week (year, week_number)
            iso_week = date.isocalendar()
            week_key = f"{iso_week[0]}-W{iso_week[1]:02d}"

            if acc['username'] in fake_usernames:
                weekly_fake[week_key] += 1
            else:
                weekly_real[week_key] += 1

        # Sort weeks
        all_weeks = sorted(set(list(weekly_real.keys()) + list(weekly_fake.keys())))

        # Build arrays for correlation
        real_counts = []
        fake_counts = []
        weeks_for_analysis = []

        for week in all_weeks:
            real = weekly_real[week]
            fake = weekly_fake[week]

            real_counts.append(real)
            fake_counts.append(fake)
            weeks_for_analysis.append(week)

        # Calculate correlation
        if len(real_counts) > 2:
            correlation, p_value = stats.pearsonr(real_counts, fake_counts)

            print(f"Pearson Correlation Coefficient: {correlation:.4f}")
            print(f"P-value: {p_value:.4e}")

            if correlation < -0.3:
                print(f"\n⚠️  NEGATIVE CORRELATION DETECTED")
                print(f"   When real stars ↓, fake stars ↑")
            elif correlation > 0.3:
                print(f"\n✓ POSITIVE CORRELATION")
                print(f"   Real and fake move together")
            else:
                print(f"\n~ WEAK/NO CORRELATION")

        # Focus on 2024 period
        print(f"\n{'='*80}")
        print("2024 PERIOD ANALYSIS (Jan 2024 onwards)")
        print(f"{'='*80}\n")

        weeks_2024 = [w for w in all_weeks if w.startswith('2024')]

        if len(weeks_2024) > 4:
            real_2024 = [weekly_real[w] for w in weeks_2024]
            fake_2024 = [weekly_fake[w] for w in weeks_2024]

            correlation_2024, p_value_2024 = stats.pearsonr(real_2024, fake_2024)

            print(f"2024 Pearson Correlation: {correlation_2024:.4f}")
            print(f"2024 P-value: {p_value_2024:.4e}")

            # Calculate week-over-week changes
            print(f"\nWeek-over-Week Change Analysis (2024):")
            print(f"Looking for inverse relationship: Real ↓ → Fake ↑\n")

            inverse_weeks = 0
            same_direction_weeks = 0

            for i in range(1, len(weeks_2024)):
                prev_real = real_2024[i-1]
                curr_real = real_2024[i]
                prev_fake = fake_2024[i-1]
                curr_fake = fake_2024[i]

                real_change = curr_real - prev_real
                fake_change = curr_fake - prev_fake

                # Check if inverse (opposite directions)
                if (real_change < 0 and fake_change > 0) or (real_change > 0 and fake_change < 0):
                    inverse_weeks += 1
                    print(f"{weeks_2024[i]}: Real {real_change:+3d} → Fake {fake_change:+3d} (INVERSE)")
                elif abs(real_change) > 5 or abs(fake_change) > 5:
                    same_direction_weeks += 1
                    print(f"{weeks_2024[i]}: Real {real_change:+3d} → Fake {fake_change:+3d}")

            total_weeks = len(weeks_2024) - 1
            inverse_pct = inverse_weeks / total_weeks * 100 if total_weeks > 0 else 0

            print(f"\n{'='*80}")
            print(f"INVERSE RELATIONSHIP SUMMARY (2024)")
            print(f"{'='*80}")
            print(f"Weeks with inverse relationship: {inverse_weeks}/{total_weeks} ({inverse_pct:.1f}%)")
            print(f"Weeks with same direction: {same_direction_weeks}/{total_weeks}")

            if inverse_pct > 40:
                print(f"\n🚨 STRONG EVIDENCE: {inverse_pct:.1f}% of weeks show inverse relationship")
                print(f"   This suggests AUTOMATIC fake star purchasing when real stars decline")
            elif inverse_pct > 25:
                print(f"\n⚠️  MODERATE EVIDENCE: {inverse_pct:.1f}% of weeks show inverse relationship")
                print(f"   Suggests possible compensatory fake star buying")

        # Moving average analysis
        print(f"\n{'='*80}")
        print("MOVING AVERAGE DEVIATION ANALYSIS")
        print(f"{'='*80}\n")

        # Calculate 4-week moving averages for 2024
        if len(weeks_2024) >= 8:
            print("Detecting periods where fake stars spike above trend when real stars drop:\n")

            window = 4
            for i in range(window, len(weeks_2024)):
                # Moving average of previous 4 weeks
                real_ma = np.mean(real_2024[i-window:i])
                fake_ma = np.mean(fake_2024[i-window:i])

                # Current week
                curr_real = real_2024[i]
                curr_fake = fake_2024[i]

                # Deviations
                real_dev = curr_real - real_ma
                fake_dev = curr_fake - fake_ma

                # If real drops below MA but fake spikes above MA
                if real_dev < -5 and fake_dev > 10:
                    print(f"{weeks_2024[i]}:")
                    print(f"  Real: {curr_real} (MA: {real_ma:.1f}, deviation: {real_dev:.1f})")
                    print(f"  Fake: {curr_fake} (MA: {fake_ma:.1f}, deviation: {fake_dev:.1f})")
                    print(f"  ⚠️  Real dropped, fake spiked - COMPENSATORY BUYING")
                    print()

        return {
            'all_weeks': all_weeks,
            'real_counts': real_counts,
            'fake_counts': fake_counts,
            'correlation': correlation if len(real_counts) > 2 else None,
            'correlation_2024': correlation_2024 if len(weeks_2024) > 4 else None,
            'inverse_weeks_2024': inverse_weeks if len(weeks_2024) > 4 else 0,
            'inverse_pct_2024': inverse_pct if len(weeks_2024) > 4 else 0
        }

    def generate_report(self, correlation_data):
        """Generate summary report."""

        print(f"\n{'='*80}")
        print("FINAL CONCLUSIONS")
        print(f"{'='*80}\n")

        if correlation_data['correlation_2024'] and correlation_data['correlation_2024'] < -0.2:
            print("EVIDENCE OF AUTOMATIC COMPENSATORY FAKE STAR BUYING:")
            print()
            print(f"1. Negative correlation in 2024: {correlation_data['correlation_2024']:.4f}")
            print(f"2. Inverse weeks: {correlation_data['inverse_pct_2024']:.1f}%")
            print()
            print("INTERPRETATION:")
            print("  When organic (real) star growth slows or declines, fake stars")
            print("  automatically increase to maintain the appearance of momentum.")
            print()
            print("  This is consistent with an automated system that:")
            print("  - Monitors real star velocity")
            print("  - Purchases fake stars to compensate for organic decline")
            print("  - Maintains steady total star growth rate")
            print()
            print("  This is NOT organic growth. This is MANAGED MANIPULATION.")

        # Save results
        output_file = self.data_dir / 'correlation_analysis.json'
        with open(output_file, 'w') as f:
            json.dump({
                'overall_correlation': correlation_data['correlation'],
                'correlation_2024': correlation_data['correlation_2024'],
                'inverse_weeks_2024': correlation_data['inverse_weeks_2024'],
                'inverse_percentage_2024': correlation_data['inverse_pct_2024'],
                'total_accounts': len(self.accounts),
                'analysis_date': datetime.now().isoformat()
            }, f, indent=2)

        print(f"\nResults saved to: {output_file}")


def main():
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║       Fake/Real Star Correlation Analysis                         ║
║       Testing: Fake stars bought when real stars decline          ║
╚════════════════════════════════════════════════════════════════════╝
""")

    analyzer = CorrelationAnalyzer()
    fake_usernames = analyzer.apply_full_detection()
    correlation_data = analyzer.analyze_weekly_correlation(fake_usernames)
    analyzer.generate_report(correlation_data)

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
