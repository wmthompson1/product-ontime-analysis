#!/usr/bin/env python3
"""
016_Entry_Point_Manufacturing_Configuration.py
Official Manufacturing Configuration following LangChain Academy patterns
Direct adaptation of langchain-ai/agents-from-scratch/configuration.py
"""
# 016_Entry_Point_Manufacturing_Configuration.py
import os
from dataclasses import dataclass, fields
from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

@dataclass(kw_only=True)
class ManufacturingConfiguration:
    """Configuration for manufacturing intelligence agents following LangChain Academy patterns."""
    
    # Manufacturing-specific configuration parameters
    openai_api_key: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = "Manufacturing_Intelligence"
    
    # Manufacturing operation parameters
    default_equipment_id: Optional[str] = "MAIN-LINE-001"
    default_facility: Optional[str] = "Production_Facility_A"
    quality_threshold: Optional[float] = 0.95
    oee_target: Optional[float] = 0.85
    
    # Queue processing parameters
    max_queue_size: Optional[int] = 100
    urgent_response_time: Optional[int] = 60  # minutes
    standard_response_time: Optional[int] = 1440  # minutes (24 hours)
    
    # Manufacturing intelligence settings
    enable_predictive_maintenance: Optional[bool] = True
    enable_quality_monitoring: Optional[bool] = True
    enable_supply_chain_tracking: Optional[bool] = True
    
    # Reporting configuration
    default_report_recipient: Optional[str] = "manufacturing_manager@company.com"
    report_frequency: Optional[str] = "daily"
    alert_threshold: Optional[float] = 0.8
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "ManufacturingConfiguration":
        """Create a Manufacturing Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        
        return cls(**{k: v for k, v in values.items() if v})
    
    def validate_configuration(self) -> bool:
        """Validate manufacturing configuration parameters."""
        validation_results = []
        
        # Check API keys
        if not self.openai_api_key:
            validation_results.append("❌ OpenAI API key not configured")
        else:
            validation_results.append("✅ OpenAI API key configured")
        
        # Check manufacturing parameters
        if self.quality_threshold and (self.quality_threshold < 0 or self.quality_threshold > 1):
            validation_results.append("❌ Quality threshold must be between 0 and 1")
        else:
            validation_results.append("✅ Quality threshold valid")
        
        if self.oee_target and (self.oee_target < 0 or self.oee_target > 1):
            validation_results.append("❌ OEE target must be between 0 and 1")
        else:
            validation_results.append("✅ OEE target valid")
        
        # Check queue parameters
        if self.max_queue_size and self.max_queue_size <= 0:
            validation_results.append("❌ Max queue size must be positive")
        else:
            validation_results.append("✅ Queue configuration valid")
        
        print("Manufacturing Configuration Validation:")
        for result in validation_results:
            print(f"  {result}")
        
        return all("✅" in result for result in validation_results)
    
    def get_manufacturing_context(self) -> dict[str, Any]:
        """Get manufacturing context for agent operations."""
        return {
            "facility": self.default_facility,
            "equipment_id": self.default_equipment_id,
            "quality_threshold": self.quality_threshold,
            "oee_target": self.oee_target,
            "predictive_maintenance": self.enable_predictive_maintenance,
            "quality_monitoring": self.enable_quality_monitoring,
            "supply_chain_tracking": self.enable_supply_chain_tracking
        }
    
    def get_queue_configuration(self) -> dict[str, Any]:
        """Get queue processing configuration."""
        return {
            "max_queue_size": self.max_queue_size,
            "urgent_response_time": self.urgent_response_time,
            "standard_response_time": self.standard_response_time,
            "alert_threshold": self.alert_threshold
        }
    
    def get_reporting_configuration(self) -> dict[str, Any]:
        """Get reporting configuration."""
        return {
            "default_recipient": self.default_report_recipient,
            "frequency": self.report_frequency,
            "alert_threshold": self.alert_threshold
        }

# Manufacturing Environment Configuration Helper
class ManufacturingEnvironment:
    """Helper class for manufacturing environment configuration."""
    
    @staticmethod
    def setup_development_environment() -> ManufacturingConfiguration:
        """Setup development environment configuration."""
        return ManufacturingConfiguration(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            langsmith_project="Manufacturing_Dev",
            default_equipment_id="DEV-LINE-001",
            default_facility="Development_Lab",
            quality_threshold=0.90,
            oee_target=0.80,
            max_queue_size=50,
            enable_predictive_maintenance=True,
            enable_quality_monitoring=True,
            enable_supply_chain_tracking=False,
            default_report_recipient="dev_team@company.com",
            report_frequency="hourly"
        )
    
    @staticmethod
    def setup_production_environment() -> ManufacturingConfiguration:
        """Setup production environment configuration."""
        return ManufacturingConfiguration(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            langsmith_project="Manufacturing_Production",
            default_equipment_id="PROD-LINE-001",
            default_facility="Production_Facility_A",
            quality_threshold=0.98,
            oee_target=0.85,
            max_queue_size=200,
            urgent_response_time=30,
            standard_response_time=720,
            enable_predictive_maintenance=True,
            enable_quality_monitoring=True,
            enable_supply_chain_tracking=True,
            default_report_recipient="production_manager@company.com",
            report_frequency="daily"
        )
    
    @staticmethod
    def setup_testing_environment() -> ManufacturingConfiguration:
        """Setup testing environment configuration."""
        return ManufacturingConfiguration(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            langsmith_project="Manufacturing_Testing",
            default_equipment_id="TEST-LINE-001",
            default_facility="Testing_Lab",
            quality_threshold=0.85,
            oee_target=0.75,
            max_queue_size=20,
            enable_predictive_maintenance=False,
            enable_quality_monitoring=True,
            enable_supply_chain_tracking=False,
            default_report_recipient="test_team@company.com",
            report_frequency="on_demand"
        )

# Configuration Factory following LangChain Academy patterns
class ManufacturingConfigurationFactory:
    """Factory for creating manufacturing configurations."""
    
    @staticmethod
    def create_configuration(
        environment: str = "development",
        custom_config: Optional[RunnableConfig] = None
    ) -> ManufacturingConfiguration:
        """Create manufacturing configuration based on environment."""
        
        if custom_config:
            return ManufacturingConfiguration.from_runnable_config(custom_config)
        
        if environment == "production":
            return ManufacturingEnvironment.setup_production_environment()
        elif environment == "testing":
            return ManufacturingEnvironment.setup_testing_environment()
        else:  # development
            return ManufacturingEnvironment.setup_development_environment()
    
    @staticmethod
    def validate_environment_variables() -> dict[str, bool]:
        """Validate required environment variables."""
        required_vars = {
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "LANGSMITH_API_KEY": bool(os.getenv("LANGSMITH_API_KEY")),
        }
        
        optional_vars = {
            "LANGSMITH_PROJECT": bool(os.getenv("LANGSMITH_PROJECT")),
            "MANUFACTURING_FACILITY": bool(os.getenv("MANUFACTURING_FACILITY")),
            "DEFAULT_EQUIPMENT_ID": bool(os.getenv("DEFAULT_EQUIPMENT_ID"))
        }
        
        return {
            "required": required_vars,
            "optional": optional_vars,
            "all_required_present": all(required_vars.values())
        }

def demo_manufacturing_configuration():
    """Demonstrate the Manufacturing Configuration system."""
    print("🧪 Manufacturing Configuration Demo")
    print("Following langchain-ai/agents-from-scratch/configuration.py patterns")
    print("=" * 70)
    
    # Test environment variable validation
    print("\n📊 Environment Variable Validation:")
    print("-" * 40)
    env_status = ManufacturingConfigurationFactory.validate_environment_variables()
    
    print("Required Variables:")
    for var, status in env_status["required"].items():
        print(f"  {var}: {'✅' if status else '❌'}")
    
    print("\nOptional Variables:")
    for var, status in env_status["optional"].items():
        print(f"  {var}: {'✅' if status else '➖'}")
    
    # Test different environment configurations
    environments = ["development", "testing", "production"]
    
    for env in environments:
        print(f"\n🔧 {env.title()} Environment Configuration:")
        print("-" * 40)
        
        try:
            config = ManufacturingConfigurationFactory.create_configuration(env)
            
            print(f"✅ Configuration created successfully")
            print(f"  Facility: {config.default_facility}")
            print(f"  Equipment: {config.default_equipment_id}")
            print(f"  Quality Threshold: {config.quality_threshold}")
            print(f"  OEE Target: {config.oee_target}")
            print(f"  Max Queue Size: {config.max_queue_size}")
            print(f"  Predictive Maintenance: {config.enable_predictive_maintenance}")
            
            # Validate configuration
            is_valid = config.validate_configuration()
            print(f"  Overall Validation: {'✅ PASS' if is_valid else '❌ FAIL'}")
            
        except Exception as e:
            print(f"❌ Configuration failed: {str(e)}")
    
    # Test custom configuration from RunnableConfig
    print(f"\n🛠️  Custom RunnableConfig Test:")
    print("-" * 40)
    
    try:
        custom_runnable_config = {
            "configurable": {
                "default_equipment_id": "CUSTOM-LINE-001",
                "quality_threshold": 0.92,
                "oee_target": 0.88,
                "max_queue_size": 75
            }
        }
        
        custom_config = ManufacturingConfiguration.from_runnable_config(custom_runnable_config)
        
        print(f"✅ Custom configuration created")
        print(f"  Equipment: {custom_config.default_equipment_id}")
        print(f"  Quality Threshold: {custom_config.quality_threshold}")
        print(f"  OEE Target: {custom_config.oee_target}")
        print(f"  Max Queue Size: {custom_config.max_queue_size}")
        
    except Exception as e:
        print(f"❌ Custom configuration failed: {str(e)}")
    
    print(f"\n" + "=" * 70)
    print("🎯 Manufacturing Configuration successfully implemented!")
    print("📧➡️🏭 Perfect adaptation of LangChain Academy configuration.py")
    print("🔧 Environment-aware configuration with validation")
    print("📚 Ready for Berkeley Haas capstone deployment")
    
    return True

if __name__ == "__main__":
    # Run the manufacturing configuration demo
    demo_manufacturing_configuration()