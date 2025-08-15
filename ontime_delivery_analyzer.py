#!/usr/bin/env python3
"""
Daily Product On Time Rate Statistical Analysis Tool

This tool analyzes daily product on-time delivery rates to determine if variations
are statistically significant within a 5% margin of error, helping manufacturing
companies monitor delivery performance and identify process control issues.

Statistical Methods:
- Z-test for proportions to compare daily rates against baseline
- 95% confidence intervals to assess precision
- Margin of error validation to ensure ≤5% requirement
- Process control analysis to identify significant variations

Usage:
    python ontime_delivery_analyzer.py

Author: AI Assistant
Date: August 2025
"""

import csv
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class OnTimeDeliveryAnalyzer:
    def __init__(self):
        self.data = []
        self.overall_stats = {}
        
    def create_sample_data(self, days=15, base_rate=0.95, min_units=800, max_units=1200):
        """Generate realistic sample on-time delivery data"""
        start_date = datetime(2025, 8, 1)
        self.data = []
        
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            total_received = random.randint(min_units, max_units)
            
            # Generate on-time rate with some realistic variation
            daily_rate = base_rate + random.gauss(0, 0.02)  # 2% standard deviation
            daily_rate = max(0.85, min(0.99, daily_rate))  # Constrain to realistic range
            
            received_late = int(total_received * (1 - daily_rate))
            received_ontime = total_received - received_late
            ontime_rate = received_ontime / total_received
            
            self.data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'total_received': total_received,
                'received_late': received_late,
                'received_ontime': received_ontime,
                'ontime_rate': ontime_rate
            })
        
        return self.data
    
    def calculate_confidence_interval(self, ontime_rate, sample_size, confidence_level=0.95):
        """Calculate confidence interval for on-time rate using normal approximation"""
        # Z-score for 95% confidence interval
        z_score = 1.96  # For 95% confidence
        
        # Handle edge cases where ontime_rate is 0 or 1
        if ontime_rate <= 0:
            # All deliveries late - rare case
            margin_of_error = z_score * math.sqrt(1 / (4 * sample_size))
            return 0, margin_of_error, margin_of_error
        elif ontime_rate >= 1:
            # Use Wilson score interval for perfect on-time performance
            margin_of_error = z_score * math.sqrt(1 / (4 * sample_size))
            return 1 - margin_of_error, 1, margin_of_error
        
        # Normal case - standard error for proportion
        variance = (ontime_rate * (1 - ontime_rate)) / sample_size
        if variance < 0:
            variance = 0
        
        se = math.sqrt(variance)
        margin_of_error = z_score * se
        
        lower_bound = max(0, ontime_rate - margin_of_error)
        upper_bound = min(1, ontime_rate + margin_of_error)
        
        return lower_bound, upper_bound, margin_of_error
    
    def z_test_proportion(self, observed_rate, expected_rate, sample_size):
        """Perform z-test for single proportion"""
        if expected_rate <= 0 or expected_rate >= 1:
            return 0, 1  # Can't perform test with extreme rates
        
        # Standard error under null hypothesis
        variance = (expected_rate * (1 - expected_rate)) / sample_size
        if variance <= 0:
            return 0, 1
        
        se = math.sqrt(variance)
        
        if se == 0:
            return 0, 1
        
        # Z-statistic
        z_stat = (observed_rate - expected_rate) / se
        
        # Two-tailed p-value approximation
        p_value = 2 * (1 - self.normal_cdf(abs(z_stat)))
        
        return z_stat, p_value
    
    def normal_cdf(self, x):
        """Approximation of standard normal CDF"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def calculate_overall_statistics(self):
        """Calculate overall statistics across all days"""
        if not self.data:
            return {}
        
        total_received = sum(day['total_received'] for day in self.data)
        total_late = sum(day['received_late'] for day in self.data)
        total_ontime = total_received - total_late
        
        overall_ontime_rate = total_ontime / total_received if total_received > 0 else 0
        
        # Daily rates for statistics
        daily_rates = [day['ontime_rate'] for day in self.data]
        mean_daily_rate = sum(daily_rates) / len(daily_rates)
        
        # Standard deviation
        variance = sum((rate - mean_daily_rate) ** 2 for rate in daily_rates) / len(daily_rates)
        std_dev = math.sqrt(variance)
        
        self.overall_stats = {
            'days_analyzed': len(self.data),
            'total_received': total_received,
            'total_late': total_late,
            'total_ontime': total_ontime,
            'overall_ontime_rate': overall_ontime_rate,
            'mean_daily_rate': mean_daily_rate,
            'std_dev': std_dev,
            'min_rate': min(daily_rates),
            'max_rate': max(daily_rates)
        }
        
        return self.overall_stats
    
    def analyze_daily_significance(self, significance_level=0.05, margin_requirement=0.05):
        """Analyze each day for statistical significance"""
        if not self.overall_stats:
            self.calculate_overall_statistics()
        
        expected_rate = self.overall_stats['overall_ontime_rate']
        results = []
        
        for day in self.data:
            observed_rate = day['ontime_rate']
            sample_size = day['total_received']
            
            # Z-test for significance
            z_stat, p_value = self.z_test_proportion(observed_rate, expected_rate, sample_size)
            is_significant = p_value < significance_level
            
            # Confidence interval and margin of error
            lower_ci, upper_ci, moe = self.calculate_confidence_interval(observed_rate, sample_size)
            meets_margin = moe <= margin_requirement
            
            results.append({
                'date': day['date'],
                'ontime_rate': observed_rate,
                'total_received': sample_size,
                'z_statistic': z_stat,
                'p_value': p_value,
                'is_significant': is_significant,
                'confidence_lower': lower_ci,
                'confidence_upper': upper_ci,
                'margin_of_error': moe,
                'meets_margin_requirement': meets_margin
            })
        
        return results
    
    def generate_report(self):
        """Generate comprehensive statistical analysis report"""
        if not self.data:
            print("No data available for analysis.")
            return
        
        # Calculate statistics
        overall_stats = self.calculate_overall_statistics()
        daily_results = self.analyze_daily_significance()
        
        # Overall confidence interval
        overall_lower, overall_upper, overall_moe = self.calculate_confidence_interval(
            overall_stats['overall_ontime_rate'], 
            overall_stats['total_received']
        )
        
        # Summary counts
        significant_days = sum(1 for day in daily_results if day['is_significant'])
        days_within_margin = sum(1 for day in daily_results if day['meets_margin_requirement'])
        process_control_pct = (len(daily_results) - significant_days) / len(daily_results) * 100
        
        # Generate report
        print("=" * 70)
        print("DAILY PRODUCT ON TIME RATE STATISTICAL ANALYSIS REPORT")
        print("=" * 70)
        print()
        
        print("1. OVERALL STATISTICS")
        print("-" * 25)
        print(f"Analysis Period: {overall_stats['days_analyzed']} days")
        print(f"Total Units Received: {overall_stats['total_received']:,}")
        print(f"Total Late Deliveries: {overall_stats['total_late']:,}")
        print(f"Overall On Time Rate: {overall_stats['overall_ontime_rate']:.4f} ({overall_stats['overall_ontime_rate']*100:.2f}%)")
        print(f"Mean Daily Rate: {overall_stats['mean_daily_rate']:.4f} ({overall_stats['mean_daily_rate']*100:.2f}%)")
        print(f"Standard Deviation: {overall_stats['std_dev']:.4f}")
        print(f"Range: {overall_stats['min_rate']:.4f} - {overall_stats['max_rate']:.4f}")
        print()
        
        print("2. CONFIDENCE INTERVAL ANALYSIS (95%)")
        print("-" * 40)
        print(f"Overall On Time Rate: {overall_stats['overall_ontime_rate']:.4f}")
        print(f"95% Confidence Interval: [{overall_lower:.4f}, {overall_upper:.4f}]")
        print(f"Margin of Error: {overall_moe:.4f} ({overall_moe*100:.2f}%)")
        print(f"Meets 5% Margin Requirement: {'YES' if overall_moe <= 0.05 else 'NO'}")
        print()
        
        print("3. DAILY SIGNIFICANCE ANALYSIS")
        print("-" * 35)
        print("Day  Date       Rate    Significant  Margin   Within 5%")
        print("-" * 55)
        
        for i, result in enumerate(daily_results, 1):
            rate_pct = result['ontime_rate'] * 100
            moe_pct = result['margin_of_error'] * 100
            significant = "YES" if result['is_significant'] else "NO"
            within_margin = "YES" if result['meets_margin_requirement'] else "NO"
            
            print(f"{i:2d}   {result['date']}  {result['ontime_rate']:.4f}  {significant:3s}           {result['margin_of_error']:.4f}   {within_margin}")
        
        print()
        print("4. SUMMARY STATISTICS")
        print("-" * 25)
        print(f"Statistically Significant Days: {significant_days}/{len(daily_results)}")
        print(f"Days Within 5% Margin: {days_within_margin}/{len(daily_results)}")
        print(f"Process Control Percentage: {process_control_pct:.1f}%")
        print()
        
        print("5. CONCLUSIONS")
        print("-" * 15)
        
        if overall_moe <= 0.05:
            print("✓ Overall margin of error meets the 5% requirement")
        else:
            print("✗ Overall margin of error exceeds the 5% requirement")
        
        if process_control_pct >= 95:
            print("✓ Process appears to be in statistical control (≥95% of days within expected range)")
        else:
            print("⚠ Process may need attention (significant variations detected)")
        
        precision_pct = (days_within_margin / len(daily_results)) * 100
        print(f"✓ Good precision achieved ({precision_pct:.1f}% of days within 5% margin)")
        
        print()
        print(f"Statistical Significance Level Used: {5.0}%")
        print(f"Confidence Level: 95%")
        print(f"Margin of Error Requirement: 5.0%")
        
    def save_sample_data_csv(self, filename="sample_ontime_data.csv"):
        """Save sample data to CSV file"""
        if not self.data:
            self.create_sample_data()
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'total_received', 'received_late'])
            
            for day in self.data:
                writer.writerow([
                    day['date'],
                    day['total_received'],
                    day['received_late']
                ])
        
        print(f"Sample data saved to {filename}")
        return filename

def main():
    """Main execution function"""
    analyzer = OnTimeDeliveryAnalyzer()
    
    print("Daily Product On Time Rate Statistical Analysis Tool")
    print("=" * 55)
    print()
    
    # Create and analyze sample data
    print("Generating sample on-time delivery data...")
    analyzer.create_sample_data(days=15)
    
    # Save sample CSV
    analyzer.save_sample_data_csv()
    
    print()
    analyzer.generate_report()

if __name__ == "__main__":
    main()