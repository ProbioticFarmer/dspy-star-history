#!/usr/bin/env python3
"""
Run Advanced CMU Detection on Collected Data
Can run at any time on whatever data has been collected so far
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

class AdvancedAnalyzer:
    """Apply advanced detection to collected enriched data."""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "github"
        self.enriched_file = self.data_dir / "full_forensic_enriched_data.jsonl"

        # Load collected data
        print("Loading collected data...")
        self.accounts = []
        with open(self.enriched_file, 'r') as f:
            for line in f:
                self.accounts.append(json.loads(line))

        print(f"Loaded {len(self.accounts)} accounts\n")

        # Separate basic results
        self.basic_fake = [a for a in self.accounts if a.get('is_suspicious') or a.get('status') == 'deleted']
        self.basic_legit = [a for a in self.accounts if not a.get('is_suspicious') and a.get('status') != 'deleted']

    def analyze_temporal_clustering(self, threshold_minutes: int = 60) -> Dict:
        """Detect temporal clustering in the collected data."""
        print(f"{'='*80}")
        print("🕐 TEMPORAL CLUSTERING ANALYSIS")
        print(f"{'='*80}\n")

        # Parse timestamps for "legit" accounts
        timestamps = []
        for account in self.basic_legit:
            ts = datetime.fromisoformat(account['starred_at'].replace('Z', '+00:00'))
            timestamps.append((account['username'], ts))

        # Sort by time
        timestamps.sort(key=lambda x: x[1])

        # Find clusters
        clusters = []
        if timestamps:
            current_cluster = [timestamps[0]]

            for username, ts in timestamps[1:]:
                last_ts = current_cluster[-1][1]
                diff_minutes = (ts - last_ts).total_seconds() / 60

                if diff_minutes <= threshold_minutes:
                    current_cluster.append((username, ts))
                else:
                    if len(current_cluster) >= 10:  # Cluster of 10+ is suspicious
                        clusters.append(current_cluster)
                    current_cluster = [(username, ts)]

            # Check last cluster
            if len(current_cluster) >= 10:
                clusters.append(current_cluster)

        print(f"Found {len(clusters)} suspicious temporal clusters (10+ stars within {threshold_minutes} min)")

        suspicious_accounts = set()
        for i, cluster in enumerate(clusters, 1):
            print(f"\n  Cluster {i}: {len(cluster)} accounts")
            print(f"    Time window: {cluster[0][1]} to {cluster[-1][1]}")
            duration = (cluster[-1][1] - cluster[0][1]).total_seconds() / 60
            print(f"    Duration: {duration:.1f} minutes")
            print(f"    Sample accounts: {', '.join([f'@{u}' for u, _ in cluster[:5]])}")
            for username, _ in cluster:
                suspicious_accounts.add(username)

        return {
            'clusters': clusters,
            'suspicious_count': len(suspicious_accounts),
            'suspicious_accounts': list(suspicious_accounts)
        }

    def analyze_dormant_accounts(self) -> Dict:
        """Detect dormant accounts that suddenly became active."""
        print(f"\n{'='*80}")
        print("💤 DORMANT ACCOUNT ANALYSIS")
        print(f"{'='*80}\n")

        suspicious_dormant = []

        for account in self.basic_legit:
            if account.get('status') == 'deleted':
                continue

            # Check if account is old but has low activity
            created = datetime.fromisoformat(account['account_created'].replace('Z', '+00:00'))
            starred = datetime.fromisoformat(account['starred_at'].replace('Z', '+00:00'))

            account_age_days = (starred - created).days
            public_repos = account.get('public_repos', 0)

            # Old account (>1 year) but very low activity = suspicious
            if account_age_days > 365 and public_repos < 3:
                suspicious_dormant.append({
                    'username': account['username'],
                    'account_age_days': account_age_days,
                    'public_repos': public_repos,
                    'followers': account.get('followers', 0),
                    'following': account.get('following', 0)
                })

        # Sort by age
        suspicious_dormant.sort(key=lambda x: x['account_age_days'], reverse=True)

        print(f"Found {len(suspicious_dormant)} dormant accounts (>1 year old, <3 repos)")

        if suspicious_dormant:
            print(f"\n  Top 10 most suspicious dormant accounts:")
            for acc in suspicious_dormant[:10]:
                years = acc['account_age_days'] / 365
                print(f"    @{acc['username']}: {years:.1f} years old, {acc['public_repos']} repos, "
                      f"{acc['followers']} followers")

        return {
            'suspicious_count': len(suspicious_dormant),
            'suspicious_accounts': [a['username'] for a in suspicious_dormant],
            'details': suspicious_dormant
        }

    def analyze_activity_diversity(self) -> Dict:
        """Check for accounts with suspicious activity patterns."""
        print(f"\n{'='*80}")
        print("🔬 ACTIVITY DIVERSITY ANALYSIS")
        print(f"{'='*80}\n")

        suspicious_low_activity = []

        for account in self.basic_legit:
            if account.get('status') == 'deleted':
                continue

            repos = account.get('public_repos', 0)
            followers = account.get('followers', 0)
            following = account.get('following', 0)

            # Very low overall activity
            if repos == 0 and followers < 5 and following < 10:
                suspicious_low_activity.append({
                    'username': account['username'],
                    'public_repos': repos,
                    'followers': followers,
                    'following': following
                })

        print(f"Found {len(suspicious_low_activity)} accounts with minimal activity")
        print(f"  (0 repos, <5 followers, <10 following)")

        return {
            'suspicious_count': len(suspicious_low_activity),
            'suspicious_accounts': [a['username'] for a in suspicious_low_activity],
            'details': suspicious_low_activity
        }

    def generate_report(self, temporal, dormant, activity):
        """Generate comprehensive report."""

        # Combine all suspicious accounts
        all_suspicious = set()
        all_suspicious.update(temporal.get('suspicious_accounts', []))
        all_suspicious.update(dormant.get('suspicious_accounts', []))
        all_suspicious.update(activity.get('suspicious_accounts', []))

        total = len(self.accounts)
        basic_fake = len(self.basic_fake)
        advanced_fake = len(all_suspicious)
        total_fake = basic_fake + advanced_fake

        print(f"\n{'='*80}")
        print("📊 FINAL RESULTS")
        print(f"{'='*80}\n")

        print(f"Accounts analyzed: {total:,}")
        print(f"Date range: {self.accounts[0]['starred_at'][:10]} to {self.accounts[-1]['starred_at'][:10]}")
        print()
        print(f"Basic detection:")
        print(f"  - Suspicious: {basic_fake} ({basic_fake/total*100:.1f}%)")
        print()
        print(f"Advanced detection (on 'legit' accounts):")
        print(f"  - Temporal clustering: {temporal['suspicious_count']}")
        print(f"  - Dormant accounts: {dormant['suspicious_count']}")
        print(f"  - Low activity: {activity['suspicious_count']}")
        print(f"  - Total advanced fake: {advanced_fake} ({advanced_fake/total*100:.1f}%)")
        print()
        print(f"TOTAL FAKE: {total_fake} / {total} = {total_fake/total*100:.1f}%")
        print(f"Legitimate: {total - total_fake} ({(total - total_fake)/total*100:.1f}%)")

        # Save results
        results = {
            'analysis_date': datetime.now().isoformat(),
            'accounts_analyzed': total,
            'date_range': {
                'start': self.accounts[0]['starred_at'],
                'end': self.accounts[-1]['starred_at']
            },
            'basic_detection': {
                'suspicious': basic_fake,
                'percentage': basic_fake/total*100
            },
            'advanced_detection': {
                'temporal_clustering': temporal['suspicious_count'],
                'dormant_accounts': dormant['suspicious_count'],
                'low_activity': activity['suspicious_count'],
                'total': advanced_fake,
                'percentage': advanced_fake/total*100
            },
            'summary': {
                'total_fake': total_fake,
                'fake_percentage': total_fake/total*100,
                'legitimate': total - total_fake,
                'legitimate_percentage': (total - total_fake)/total*100
            }
        }

        output_file = self.data_dir / 'advanced_analysis_on_collected.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

        return results


def main():
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║       Advanced CMU Analysis on Collected Data                     ║
╚════════════════════════════════════════════════════════════════════╝
""")

    analyzer = AdvancedAnalyzer()

    # Run all analyses
    temporal = analyzer.analyze_temporal_clustering()
    dormant = analyzer.analyze_dormant_accounts()
    activity = analyzer.analyze_activity_diversity()

    # Generate report
    analyzer.generate_report(temporal, dormant, activity)


if __name__ == "__main__":
    main()
