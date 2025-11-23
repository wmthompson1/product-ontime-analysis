
    def _handle_urgent_request(self, state: ManufacturingState) -> ManufacturingState:
        """Handle urgent manufacturing requests"""
        print("🚨 Processing urgent manufacturing request...")
        
        try:
            # Immediate equipment health check
            health_report = monitor_equipment_health.invoke({})
            state.analysis_results["urgent_health_check"] = json.loads(health_report)
            
            # Generate urgent report
            report_result = write_manufacturing_report.invoke({
                "to": "Manufacturing Manager",
                "subject": "URGENT: Manufacturing Issue Response",
                "content": f"Urgent analysis for: {state.request}"
            })
            state.reports_generated.append(report_result)
            
            state.recommendations.append("Immediate attention required - review urgent analysis")
            print("✅ Urgent request processed")
            
        except Exception as e:
            print(f"❌ Urgent request processing failed: {str(e)}")
        
        return state
    
    def _handle_standard_request(self, state: ManufacturingState) -> ManufacturingState:
        """Handle standard manufacturing requests"""
        print("🔧 Processing standard manufacturing request...")
        
        try:
            request_lower = state.request.lower()
            
            if "oee" in request_lower or "efficiency" in request_lower:
                # OEE analysis
                oee_analysis = analyze_oee_metrics.invoke({})
                state.analysis_results["oee_analysis"] = json.loads(oee_analysis)
                
            elif "defect" in request_lower or "quality" in request_lower:
                # Defect rate analysis
                defect_analysis = analyze_defect_rates.invoke({})
                state.analysis_results["defect_analysis"] = json.loads(defect_analysis)
                
            elif "maintenance" in request_lower or "schedule" in request_lower:
                # Schedule maintenance
                maintenance_result = schedule_maintenance.invoke({
                    "equipment_id": "MAIN-LINE-001",
                    "maintenance_type": "preventive",
                    "date": "2024-02-15"
                })
                state.scheduled_tasks.append(maintenance_result)
                
            else:
                # Default to OEE analysis
                oee_analysis = analyze_oee_metrics.invoke({})
                state.analysis_results["general_analysis"] = json.loads(oee_analysis)
            
            state.recommendations.append("Standard analysis completed - review results")
            print("✅ Standard request processed")
            
        except Exception as e:
            print(f"❌ Standard request processing failed: {str(e)}")
        
        return state
    
    def _handle_monitoring_request(self, state: ManufacturingState) -> ManufacturingState:
        """Handle monitoring manufacturing requests"""
        print("📊 Processing monitoring manufacturing request...")
        
        try:
            # Equipment health monitoring
            health_report = monitor_equipment_health.invoke({})
            state.analysis_results["health_monitoring"] = json.loads(health_report)
            
            # Supply chain risk assessment
            risk_assessment = assess_supply_chain_risk.invoke({})
            state.risk_assessments.append(risk_assessment)
            
            state.recommendations.append("Monitoring data updated - review trends and alerts")
            print("✅ Monitoring request processed")
            
        except Exception as e:
            print(f"❌ Monitoring request processing failed: {str(e)}")
        
        return state 
    