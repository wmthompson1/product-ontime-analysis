"""
Daily Product Defect Rate Statistical Significance Analyzer

This tool helps determine if daily product defect rates are statistically significant
within a 5% margin of error using appropriate statistical tests.
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class DefectRateAnalyzer:
    def __init__(self):
        self.data = None
        self.alpha = 0.05  # 5% significance level
        self.margin_of_error = 0.05  # 5% margin of error
        
    def load_data_from_csv(self, filepath):
        """Load defect data from CSV file"""
        try:
            self.data = pd.read_csv(filepath)
            print(f"Data loaded successfully: {len(self.data)} records")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def create_sample_data(self, days=30, baseline_defect_rate=0.02):
        """Create sample defect data for demonstration"""
        np.random.seed(42)
        dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
        
        # Simulate daily production and defects
        daily_production = np.random.normal(1000, 100, days).astype(int)
        daily_production = np.maximum(daily_production, 500)  # Minimum 500 units
        
        # Simulate defects with some variation around baseline rate
        defect_rates = np.random.normal(baseline_defect_rate, 0.005, days)
        defect_rates = np.maximum(defect_rates, 0)  # No negative defect rates
        
        daily_defects = (daily_production * defect_rates).astype(int)
        
        self.data = pd.DataFrame({
            'date': dates,
            'total_produced': daily_production,
            'defective_units': daily_defects,
            'defect_rate': daily_defects / daily_production
        })
        
        print(f"Sample data created: {len(self.data)} days of production data")
        return self.data
    
    def calculate_confidence_interval(self, defect_rate, sample_size, confidence_level=0.95):
        """Calculate confidence interval for defect rate"""
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        
        # Standard error for proportion
        se = np.sqrt((defect_rate * (1 - defect_rate)) / sample_size)
        
        margin_of_error = z_score * se
        
        lower_bound = defect_rate - margin_of_error
        upper_bound = defect_rate + margin_of_error
        
        return lower_bound, upper_bound, margin_of_error
    
    def test_single_day_significance(self, day_index, expected_rate=None):
        """Test if a single day's defect rate is statistically significant"""
        if self.data is None:
            return None
            
        row = self.data.iloc[day_index]
        observed_rate = row['defect_rate']
        sample_size = row['total_produced']
        
        if expected_rate is None:
            # Use overall average as expected rate
            expected_rate = self.data['defect_rate'].mean()
        
        # One-sample proportion test (z-test)
        observed_defects = row['defective_units']
        expected_defects = expected_rate * sample_size
        
        # Z-test for proportion
        z_stat = (observed_defects - expected_defects) / np.sqrt(expected_defects * (1 - expected_rate))
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # Confidence interval
        lower_ci, upper_ci, moe = self.calculate_confidence_interval(observed_rate, sample_size)
        
        result = {
            'date': row['date'],
            'observed_rate': observed_rate,
            'expected_rate': expected_rate,
            'sample_size': sample_size,
            'z_statistic': z_stat,
            'p_value': p_value,
            'is_significant': p_value < self.alpha,
            'confidence_interval': (lower_ci, upper_ci),
            'margin_of_error': moe,
            'within_5_percent_margin': moe <= self.margin_of_error
        }
        
        return result
    
    def analyze_trend_significance(self):
        """Analyze if there's a significant trend in defect rates over time"""
        if self.data is None:
            return None
            
        # Create time index
        self.data['day_number'] = range(len(self.data))
        
        # Linear regression to test for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            self.data['day_number'], self.data['defect_rate']
        )
        
        # Mann-Kendall trend test (non-parametric)
        def mann_kendall_test(data):
            n = len(data)
            s = 0
            for i in range(n-1):
                for j in range(i+1, n):
                    if data[j] > data[i]:
                        s += 1
                    elif data[j] < data[i]:
                        s -= 1
            
            # Variance calculation
            var_s = n * (n - 1) * (2 * n + 5) / 18
            
            if s > 0:
                z = (s - 1) / np.sqrt(var_s)
            elif s < 0:
                z = (s + 1) / np.sqrt(var_s)
            else:
                z = 0
                
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))
            return z, p_value
        
        mk_z, mk_p = mann_kendall_test(self.data['defect_rate'].values)
        
        result = {
            'linear_regression': {
                'slope': slope,
                'r_squared': r_value**2,
                'p_value': p_value,
                'is_significant': p_value < self.alpha
            },
            'mann_kendall': {
                'z_statistic': mk_z,
                'p_value': mk_p,
                'is_significant': mk_p < self.alpha,
                'trend_direction': 'increasing' if mk_z > 0 else 'decreasing' if mk_z < 0 else 'no trend'
            }
        }
        
        return result
    
    def control_chart_analysis(self, control_limits_sigma=3):
        """Perform statistical process control analysis"""
        if self.data is None:
            return None
            
        mean_rate = self.data['defect_rate'].mean()
        std_rate = self.data['defect_rate'].std()
        
        # Control limits
        ucl = mean_rate + control_limits_sigma * std_rate
        lcl = max(0, mean_rate - control_limits_sigma * std_rate)
        
        # Identify out-of-control points
        out_of_control = (self.data['defect_rate'] > ucl) | (self.data['defect_rate'] < lcl)
        
        result = {
            'center_line': mean_rate,
            'upper_control_limit': ucl,
            'lower_control_limit': lcl,
            'out_of_control_points': self.data[out_of_control].to_dict('records'),
            'process_capability': {
                'within_limits': (~out_of_control).sum(),
                'out_of_limits': out_of_control.sum(),
                'percentage_in_control': (~out_of_control).mean() * 100
            }
        }
        
        return result
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive statistical analysis report"""
        if self.data is None:
            print("No data loaded. Please load data first.")
            return
            
        print("=" * 60)
        print("DAILY PRODUCT DEFECT RATE STATISTICAL ANALYSIS REPORT")
        print("=" * 60)
        
        # Basic statistics
        print("\n1. DESCRIPTIVE STATISTICS")
        print("-" * 30)
        print(f"Number of days analyzed: {len(self.data)}")
        print(f"Total units produced: {self.data['total_produced'].sum():,}")
        print(f"Total defective units: {self.data['defective_units'].sum():,}")
        print(f"Overall defect rate: {self.data['defect_rate'].mean():.4f} ({self.data['defect_rate'].mean()*100:.2f}%)")
        print(f"Standard deviation: {self.data['defect_rate'].std():.4f}")
        print(f"Min defect rate: {self.data['defect_rate'].min():.4f}")
        print(f"Max defect rate: {self.data['defect_rate'].max():.4f}")
        
        # Overall confidence interval
        overall_rate = self.data['defective_units'].sum() / self.data['total_produced'].sum()
        total_production = self.data['total_produced'].sum()
        lower_ci, upper_ci, moe = self.calculate_confidence_interval(overall_rate, total_production)
        
        print(f"\n2. OVERALL CONFIDENCE INTERVAL (95%)")
        print("-" * 35)
        print(f"Overall defect rate: {overall_rate:.4f} ({overall_rate*100:.2f}%)")
        print(f"95% Confidence Interval: [{lower_ci:.4f}, {upper_ci:.4f}]")
        print(f"Margin of Error: {moe:.4f} ({moe*100:.2f}%)")
        print(f"Within 5% margin requirement: {'YES' if moe <= self.margin_of_error else 'NO'}")
        
        # Trend analysis
        print(f"\n3. TREND ANALYSIS")
        print("-" * 20)
        trend_results = self.analyze_trend_significance()
        if trend_results:
            lr = trend_results['linear_regression']
            mk = trend_results['mann_kendall']
            
            print(f"Linear regression slope: {lr['slope']:.6f}")
            print(f"R-squared: {lr['r_squared']:.4f}")
            print(f"Linear trend significant: {'YES' if lr['is_significant'] else 'NO'} (p={lr['p_value']:.4f})")
            print(f"Mann-Kendall trend: {mk['trend_direction']}")
            print(f"Mann-Kendall significant: {'YES' if mk['is_significant'] else 'NO'} (p={mk['p_value']:.4f})")
        
        # Control chart analysis
        print(f"\n4. PROCESS CONTROL ANALYSIS")
        print("-" * 30)
        control_results = self.control_chart_analysis()
        if control_results:
            print(f"Center line (mean): {control_results['center_line']:.4f}")
            print(f"Upper control limit: {control_results['upper_control_limit']:.4f}")
            print(f"Lower control limit: {control_results['lower_control_limit']:.4f}")
            print(f"Days within control: {control_results['process_capability']['within_limits']}")
            print(f"Days out of control: {control_results['process_capability']['out_of_limits']}")
            print(f"Process control percentage: {control_results['process_capability']['percentage_in_control']:.1f}%")
        
        # Daily significance analysis
        print(f"\n5. DAILY SIGNIFICANCE ANALYSIS")
        print("-" * 35)
        significant_days = 0
        days_within_margin = 0
        
        for i in range(min(10, len(self.data))):  # Show first 10 days
            result = self.test_single_day_significance(i)
            if result:
                if result['is_significant']:
                    significant_days += 1
                if result['within_5_percent_margin']:
                    days_within_margin += 1
                    
                print(f"Day {i+1} ({result['date'].strftime('%Y-%m-%d')}): "
                      f"Rate={result['observed_rate']:.4f}, "
                      f"Significant={'YES' if result['is_significant'] else 'NO'}, "
                      f"Margin={result['margin_of_error']:.4f}")
        
        if len(self.data) > 10:
            print(f"... (showing first 10 of {len(self.data)} days)")
        
        print(f"\n6. SUMMARY CONCLUSIONS")
        print("-" * 25)
        print(f"Statistical significance level: {self.alpha*100}%")
        print(f"Required margin of error: {self.margin_of_error*100}%")
        print(f"Overall margin of error achieved: {moe*100:.2f}%")
        print(f"Meets margin requirement: {'YES' if moe <= self.margin_of_error else 'NO'}")
        
        if trend_results and trend_results['mann_kendall']['is_significant']:
            print(f"Significant trend detected: {trend_results['mann_kendall']['trend_direction']}")
        else:
            print("No significant trend detected in defect rates")
            
        if control_results and control_results['process_capability']['percentage_in_control'] >= 95:
            print("Process appears to be in statistical control")
        else:
            print("Process may be out of statistical control - investigate special causes")
    
    def create_visualizations(self):
        """Create statistical visualizations"""
        if self.data is None:
            print("No data loaded. Please load data first.")
            return
            
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Daily Product Defect Rate Statistical Analysis', fontsize=16, fontweight='bold')
        
        # 1. Time series plot with control limits
        ax1 = axes[0, 0]
        control_results = self.control_chart_analysis()
        
        ax1.plot(self.data.index, self.data['defect_rate'], 'b-o', markersize=4, linewidth=1.5, label='Daily Rate')
        ax1.axhline(y=control_results['center_line'], color='g', linestyle='-', label='Center Line')
        ax1.axhline(y=control_results['upper_control_limit'], color='r', linestyle='--', label='UCL')
        ax1.axhline(y=control_results['lower_control_limit'], color='r', linestyle='--', label='LCL')
        
        # Highlight out-of-control points
        out_of_control = ((self.data['defect_rate'] > control_results['upper_control_limit']) | 
                         (self.data['defect_rate'] < control_results['lower_control_limit']))
        if out_of_control.any():
            ax1.scatter(self.data.index[out_of_control], self.data['defect_rate'][out_of_control], 
                       color='red', s=50, zorder=5, label='Out of Control')
        
        ax1.set_title('Control Chart - Defect Rate Over Time')
        ax1.set_xlabel('Day')
        ax1.set_ylabel('Defect Rate')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Histogram with normal distribution overlay
        ax2 = axes[0, 1]
        ax2.hist(self.data['defect_rate'], bins=15, density=True, alpha=0.7, color='skyblue', edgecolor='black')
        
        # Fit and plot normal distribution
        mu, sigma = stats.norm.fit(self.data['defect_rate'])
        x = np.linspace(self.data['defect_rate'].min(), self.data['defect_rate'].max(), 100)
        ax2.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, label=f'Normal Fit (μ={mu:.4f}, σ={sigma:.4f})')
        
        ax2.set_title('Distribution of Daily Defect Rates')
        ax2.set_xlabel('Defect Rate')
        ax2.set_ylabel('Density')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Confidence intervals plot
        ax3 = axes[1, 0]
        confidence_intervals = []
        margins_of_error = []
        
        for i in range(len(self.data)):
            result = self.test_single_day_significance(i)
            if result:
                confidence_intervals.append(result['confidence_interval'])
                margins_of_error.append(result['margin_of_error'])
        
        if confidence_intervals:
            lower_bounds = [ci[0] for ci in confidence_intervals]
            upper_bounds = [ci[1] for ci in confidence_intervals]
            
            ax3.fill_between(range(len(lower_bounds)), lower_bounds, upper_bounds, 
                           alpha=0.3, color='lightblue', label='95% Confidence Interval')
            ax3.plot(range(len(self.data)), self.data['defect_rate'], 'bo-', markersize=3, label='Observed Rate')
            
            # Highlight days exceeding 5% margin of error
            exceed_margin = [i for i, moe in enumerate(margins_of_error) if moe > self.margin_of_error]
            if exceed_margin:
                ax3.scatter(exceed_margin, [self.data['defect_rate'].iloc[i] for i in exceed_margin], 
                           color='red', s=50, zorder=5, label='Exceeds 5% Margin')
        
        ax3.set_title('Daily Confidence Intervals (95%)')
        ax3.set_xlabel('Day')
        ax3.set_ylabel('Defect Rate')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Process capability analysis
        ax4 = axes[1, 1]
        
        # Calculate daily margins of error
        daily_margins = [self.test_single_day_significance(i)['margin_of_error'] for i in range(len(self.data))]
        
        ax4.bar(range(len(daily_margins)), daily_margins, color='lightgreen', alpha=0.7, 
               label='Daily Margin of Error')
        ax4.axhline(y=self.margin_of_error, color='red', linestyle='--', linewidth=2, 
                   label=f'5% Requirement')
        
        ax4.set_title('Daily Margin of Error vs. 5% Requirement')
        ax4.set_xlabel('Day')
        ax4.set_ylabel('Margin of Error')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('defect_rate_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("Visualizations saved as 'defect_rate_analysis.png'")

def main():
    """Main function to run the defect rate analysis"""
    analyzer = DefectRateAnalyzer()
    
    print("Daily Product Defect Rate Statistical Significance Analyzer")
    print("=" * 60)
    
    # Create sample data for demonstration
    print("\nCreating sample data for demonstration...")
    sample_data = analyzer.create_sample_data(days=30, baseline_defect_rate=0.025)
    
    print("\nSample data preview:")
    print(sample_data.head())
    
    # Generate comprehensive report
    analyzer.generate_comprehensive_report()
    
    # Create visualizations
    print(f"\nGenerating statistical visualizations...")
    analyzer.create_visualizations()
    
    print(f"\nAnalysis complete! Check 'defect_rate_analysis.png' for visualizations.")
    
    # Instructions for using with real data
    print(f"\n" + "="*60)
    print("TO USE WITH YOUR REAL DATA:")
    print("="*60)
    print("1. Prepare a CSV file with columns: 'date', 'total_produced', 'defective_units'")
    print("2. Use: analyzer.load_data_from_csv('your_data.csv')")
    print("3. Run: analyzer.generate_comprehensive_report()")
    print("4. Run: analyzer.create_visualizations()")

if __name__ == "__main__":
    main()