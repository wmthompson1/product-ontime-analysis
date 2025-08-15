"""
Simple Daily Product Defect Rate Statistical Significance Analyzer

A lightweight version that uses built-in statistics and math modules
to determine if daily product defect rates are statistically significant
within a 5% margin of error.
"""

import math
import csv
import statistics
from datetime import datetime, timedelta

class SimpleDefectAnalyzer:
    def __init__(self):
        self.data = []
        self.alpha = 0.05  # 5% significance level
        self.margin_of_error_limit = 0.05  # 5% margin of error requirement
    
    def create_sample_data(self, days=15):
        """Create sample defect data for demonstration"""
        # Sample data with realistic production numbers
        sample_data = [
            {'date': '2025-08-01', 'total_produced': 1050, 'defective_units': 23},
            {'date': '2025-08-02', 'total_produced': 980, 'defective_units': 19},
            {'date': '2025-08-03', 'total_produced': 1120, 'defective_units': 28},
            {'date': '2025-08-04', 'total_produced': 1010, 'defective_units': 25},
            {'date': '2025-08-05', 'total_produced': 1200, 'defective_units': 31},
            {'date': '2025-08-06', 'total_produced': 890, 'defective_units': 18},
            {'date': '2025-08-07', 'total_produced': 1100, 'defective_units': 22},
            {'date': '2025-08-08', 'total_produced': 1050, 'defective_units': 26},
            {'date': '2025-08-09', 'total_produced': 950, 'defective_units': 20},
            {'date': '2025-08-10', 'total_produced': 1080, 'defective_units': 24},
            {'date': '2025-08-11', 'total_produced': 1150, 'defective_units': 29},
            {'date': '2025-08-12', 'total_produced': 1020, 'defective_units': 21},
            {'date': '2025-08-13', 'total_produced': 1070, 'defective_units': 25},
            {'date': '2025-08-14', 'total_produced': 990, 'defective_units': 19},
            {'date': '2025-08-15', 'total_produced': 1130, 'defective_units': 27}
        ]
        
        self.data = []
        for row in sample_data[:days]:
            defect_rate = row['defective_units'] / row['total_produced']
            self.data.append({
                'date': row['date'],
                'total_produced': row['total_produced'],
                'defective_units': row['defective_units'],
                'defect_rate': defect_rate
            })
        
        return self.data
    
    def calculate_confidence_interval(self, defect_rate, sample_size, confidence_level=0.95):
        """Calculate confidence interval for defect rate using normal approximation"""
        # Z-score for 95% confidence interval
        z_score = 1.96  # For 95% confidence
        
        # Standard error for proportion
        se = math.sqrt((defect_rate * (1 - defect_rate)) / sample_size)
        
        margin_of_error = z_score * se
        
        lower_bound = max(0, defect_rate - margin_of_error)
        upper_bound = min(1, defect_rate + margin_of_error)
        
        return lower_bound, upper_bound, margin_of_error
    
    def z_test_proportion(self, observed_rate, expected_rate, sample_size):
        """Perform z-test for single proportion"""
        if expected_rate == 0 or expected_rate == 1:
            return 0, 1  # Can't perform test
        
        # Standard error under null hypothesis
        se = math.sqrt((expected_rate * (1 - expected_rate)) / sample_size)
        
        if se == 0:
            return 0, 1
        
        # Z-statistic
        z_stat = (observed_rate - expected_rate) / se
        
        # Two-tailed p-value approximation
        p_value = 2 * (1 - self.normal_cdf(abs(z_stat)))
        
        return z_stat, p_value
    
    def normal_cdf(self, x):
        """Approximation of normal cumulative distribution function"""
        # Using the error function approximation
        return 0.5 * (1 + self.erf(x / math.sqrt(2)))
    
    def erf(self, x):
        """Error function approximation"""
        # Abramowitz and Stegun approximation
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911
        
        sign = 1 if x >= 0 else -1
        x = abs(x)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return sign * y
    
    def analyze_daily_significance(self):
        """Analyze each day for statistical significance"""
        if not self.data:
            return []
        
        # Calculate overall defect rate as baseline
        total_defects = sum(d['defective_units'] for d in self.data)
        total_production = sum(d['total_produced'] for d in self.data)
        overall_rate = total_defects / total_production
        
        results = []
        
        for i, day_data in enumerate(self.data):
            observed_rate = day_data['defect_rate']
            sample_size = day_data['total_produced']
            
            # Statistical test
            z_stat, p_value = self.z_test_proportion(observed_rate, overall_rate, sample_size)
            
            # Confidence interval
            lower_ci, upper_ci, moe = self.calculate_confidence_interval(observed_rate, sample_size)
            
            result = {
                'day': i + 1,
                'date': day_data['date'],
                'observed_rate': observed_rate,
                'sample_size': sample_size,
                'z_statistic': z_stat,
                'p_value': p_value,
                'is_significant': p_value < self.alpha,
                'confidence_interval': (lower_ci, upper_ci),
                'margin_of_error': moe,
                'within_5_percent_margin': moe <= self.margin_of_error_limit
            }
            
            results.append(result)
        
        return results
    
    def analyze_overall_statistics(self):
        """Calculate overall statistics"""
        if not self.data:
            return None
        
        # Basic statistics
        defect_rates = [d['defect_rate'] for d in self.data]
        total_defects = sum(d['defective_units'] for d in self.data)
        total_production = sum(d['total_produced'] for d in self.data)
        
        overall_rate = total_defects / total_production
        mean_rate = statistics.mean(defect_rates)
        std_dev = statistics.stdev(defect_rates) if len(defect_rates) > 1 else 0
        
        # Overall confidence interval
        lower_ci, upper_ci, moe = self.calculate_confidence_interval(overall_rate, total_production)
        
        return {
            'days_analyzed': len(self.data),
            'total_production': total_production,
            'total_defects': total_defects,
            'overall_defect_rate': overall_rate,
            'mean_daily_rate': mean_rate,
            'std_deviation': std_dev,
            'min_rate': min(defect_rates),
            'max_rate': max(defect_rates),
            'overall_confidence_interval': (lower_ci, upper_ci),
            'overall_margin_of_error': moe,
            'meets_margin_requirement': moe <= self.margin_of_error_limit
        }
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        if not self.data:
            print("No data available for analysis")
            return
        
        print("=" * 70)
        print("DAILY PRODUCT DEFECT RATE STATISTICAL ANALYSIS REPORT")
        print("=" * 70)
        
        # Overall statistics
        overall_stats = self.analyze_overall_statistics()
        
        print("\n1. OVERALL STATISTICS")
        print("-" * 25)
        print(f"Analysis Period: {len(self.data)} days")
        print(f"Total Units Produced: {overall_stats['total_production']:,}")
        print(f"Total Defective Units: {overall_stats['total_defects']:,}")
        print(f"Overall Defect Rate: {overall_stats['overall_defect_rate']:.4f} ({overall_stats['overall_defect_rate']*100:.2f}%)")
        print(f"Mean Daily Rate: {overall_stats['mean_daily_rate']:.4f} ({overall_stats['mean_daily_rate']*100:.2f}%)")
        print(f"Standard Deviation: {overall_stats['std_deviation']:.4f}")
        print(f"Range: {overall_stats['min_rate']:.4f} - {overall_stats['max_rate']:.4f}")
        
        print("\n2. CONFIDENCE INTERVAL ANALYSIS (95%)")
        print("-" * 40)
        ci_lower, ci_upper = overall_stats['overall_confidence_interval']
        moe = overall_stats['overall_margin_of_error']
        
        print(f"Overall Defect Rate: {overall_stats['overall_defect_rate']:.4f}")
        print(f"95% Confidence Interval: [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"Margin of Error: {moe:.4f} ({moe*100:.2f}%)")
        print(f"Meets 5% Margin Requirement: {'YES' if overall_stats['meets_margin_requirement'] else 'NO'}")
        
        # Daily analysis
        daily_results = self.analyze_daily_significance()
        
        print("\n3. DAILY SIGNIFICANCE ANALYSIS")
        print("-" * 35)
        print("Day  Date       Rate    Significant  Margin   Within 5%")
        print("-" * 55)
        
        significant_days = 0
        days_within_margin = 0
        
        for result in daily_results:
            if result['is_significant']:
                significant_days += 1
            if result['within_5_percent_margin']:
                days_within_margin += 1
            
            print(f"{result['day']:2d}   {result['date']}  {result['observed_rate']:.4f}  "
                  f"{'YES' if result['is_significant'] else 'NO':11s}  "
                  f"{result['margin_of_error']:.4f}   {'YES' if result['within_5_percent_margin'] else 'NO'}")
        
        print("\n4. SUMMARY STATISTICS")
        print("-" * 25)
        print(f"Statistically Significant Days: {significant_days}/{len(daily_results)}")
        print(f"Days Within 5% Margin: {days_within_margin}/{len(daily_results)}")
        print(f"Process Control Percentage: {((len(daily_results) - significant_days) / len(daily_results) * 100):.1f}%")
        
        print("\n5. CONCLUSIONS")
        print("-" * 15)
        
        if overall_stats['meets_margin_requirement']:
            print("✓ Overall margin of error meets the 5% requirement")
        else:
            print("✗ Overall margin of error exceeds the 5% requirement")
            print("  Recommendation: Increase sample size (daily production)")
        
        control_percentage = (len(daily_results) - significant_days) / len(daily_results) * 100
        if control_percentage >= 95:
            print("✓ Process appears to be in statistical control (≥95% of days within expected range)")
        else:
            print(f"⚠ Process may need attention ({control_percentage:.1f}% of days within expected range)")
            print("  Recommendation: Investigate special causes for significant variations")
        
        margin_percentage = days_within_margin / len(daily_results) * 100
        if margin_percentage >= 80:
            print(f"✓ Good precision achieved ({margin_percentage:.1f}% of days within 5% margin)")
        else:
            print(f"⚠ Consider larger daily production to improve precision ({margin_percentage:.1f}% within margin)")
        
        print(f"\nStatistical Significance Level Used: {self.alpha*100}%")
        print(f"Confidence Level: 95%")
        print(f"Margin of Error Requirement: {self.margin_of_error_limit*100}%")

def main():
    """Main function to run the defect rate analysis"""
    analyzer = SimpleDefectAnalyzer()
    
    print("Daily Product Defect Rate Statistical Significance Analyzer")
    print("=" * 60)
    print("Determining if defect rates are statistically significant within 5% margin of error")
    
    # Create and analyze sample data
    print(f"\nGenerating sample production data...")
    sample_data = analyzer.create_sample_data(days=15)
    
    print(f"Sample data created: {len(sample_data)} days of production data")
    print(f"\nFirst 5 days preview:")
    for i, day in enumerate(sample_data[:5]):
        print(f"  Day {i+1}: {day['total_produced']} units, {day['defective_units']} defects, "
              f"rate = {day['defect_rate']:.4f}")
    
    # Generate comprehensive analysis
    analyzer.generate_report()
    
    print(f"\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("To use with your own data:")
    print("1. Prepare CSV with columns: date, total_produced, defective_units")
    print("2. Modify the script to load your data")
    print("3. Run the analysis to get statistical significance results")

if __name__ == "__main__":
    main()