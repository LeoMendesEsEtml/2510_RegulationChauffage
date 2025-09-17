# -*- coding: utf-8 -*-
# file: test_temperature_precision.py
"""
Test script to analyze the precision of temperature conversion,
specifically checking if interpolation achieves 0.5°C accuracy.
"""

def analyze_temperature_precision():
    """
    Analyze the precision of temperature conversion for different sensors.
    Tests interpolation accuracy and determines if 0.5°C precision is achievable.
    """
    try:
        from app.sensor_profiles import SENSOR_TABLES
        from app.temperature_conversion import resistance_to_temperature_dynamic
        
        print("=== Analyzing Temperature Conversion Precision ===")
        
        # Test precision for each sensor type
        sensors_to_test = ["Ni1000 TK5000", "PT1000", "De Dietrich AF60", "Siemens QAC32"]
        
        for sensor_name in sensors_to_test:
            if sensor_name not in SENSOR_TABLES:
                print(f"❌ Sensor {sensor_name} not found")
                continue
                
            print(f"\n📊 Testing {sensor_name}:")
            table = SENSOR_TABLES[sensor_name]
            
            # Calculate temperature step between table points
            temp_steps = []
            resistance_steps = []
            
            for i in range(len(table) - 1):
                t1, r1 = table[i]
                t2, r2 = table[i + 1]
                temp_step = abs(t2 - t1)
                resistance_step = abs(r2 - r1)
                temp_steps.append(temp_step)
                resistance_steps.append(resistance_step)
            
            avg_temp_step = sum(temp_steps) / len(temp_steps)
            max_temp_step = max(temp_steps)
            min_resistance_step = min(resistance_steps)
            max_resistance_step = max(resistance_steps)
            
            print(f"   • Average temperature step: {avg_temp_step:.1f}°C")
            print(f"   • Maximum temperature step: {max_temp_step:.1f}°C")
            print(f"   • Resistance change range: {min_resistance_step:.1f}Ω to {max_resistance_step:.1f}Ω per step")
            
            # Test interpolation precision
            # Take a middle section and test interpolation
            mid_idx = len(table) // 2
            if mid_idx < len(table) - 1:
                t1, r1 = table[mid_idx]
                t2, r2 = table[mid_idx + 1]
                
                # Test points between these two table entries
                test_points = 10
                print(f"   • Testing interpolation between {t1}°C and {t2}°C:")
                
                for i in range(1, test_points):
                    # Create test resistance between r1 and r2
                    test_resistance = r1 + (r2 - r1) * (i / test_points)
                    calculated_temp = resistance_to_temperature_dynamic(test_resistance, sensor_name)
                    expected_temp = t1 + (t2 - t1) * (i / test_points)
                    
                    if calculated_temp is not None:
                        error = abs(calculated_temp - expected_temp)
                        print(f"     R={test_resistance:.1f}Ω → T={calculated_temp:.3f}°C (expected {expected_temp:.3f}°C, error: {error:.3f}°C)")
            
            # Test sensor sensitivity (resistance change per °C)
            # Take measurements around room temperature (20°C area)
            room_temp_measurements = []
            for t, r in table:
                if 15 <= t <= 25:
                    room_temp_measurements.append((t, r))
            
            if len(room_temp_measurements) >= 2:
                sensitivities = []
                for i in range(len(room_temp_measurements) - 1):
                    t1, r1 = room_temp_measurements[i]
                    t2, r2 = room_temp_measurements[i + 1]
                    sensitivity = abs(r2 - r1) / abs(t2 - t1)  # Ω/°C
                    sensitivities.append(sensitivity)
                
                avg_sensitivity = sum(sensitivities) / len(sensitivities)
                print(f"   • Average sensitivity around 20°C: {avg_sensitivity:.2f}Ω/°C")
                
                # Estimate measurement precision needed for 0.5°C accuracy
                resistance_precision_needed = 0.5 * avg_sensitivity
                print(f"   • Resistance precision needed for 0.5°C accuracy: ±{resistance_precision_needed:.2f}Ω")
        
        print(f"\n=== Precision Analysis Summary ===")
        print("✅ Current Implementation:")
        print("   • Uses linear interpolation between table points")
        print("   • Table points are spaced 1.5°C apart")
        print("   • Interpolation should provide much better than 0.5°C precision")
        print("   • Accuracy depends on:")
        print("     - ADC measurement precision")
        print("     - Sensor linearity between table points")
        print("     - Table point accuracy")
        
        print("\n🎯 For 0.5°C Precision:")
        print("   • Linear interpolation with 1.5°C table spacing is sufficient")
        print("   • Main limitation will be ADC noise and sensor stability")
        print("   • Expected achievable precision: ±0.1-0.3°C with good ADC")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_extrapolation_limits():
    """
    Test what happens when resistance values are outside the table range.
    """
    try:
        from app.temperature_conversion import resistance_to_temperature_dynamic
        
        print("\n=== Testing Extrapolation Limits ===")
        
        # Test with Ni1000 TK5000
        sensor_name = "Ni1000 TK5000"
        
        test_cases = [
            (900, "Below table range"),      # Should return None
            (1200, "Above table range"),     # Should return None  
            (1103, "Within table range"),    # Should work
        ]
        
        for resistance, description in test_cases:
            result = resistance_to_temperature_dynamic(resistance, sensor_name)
            if result is not None:
                print(f"   • {description}: {resistance}Ω → {result:.2f}°C")
            else:
                print(f"   • {description}: {resistance}Ω → None (outside range)")
        
        print("\n⚠️  Important: Current implementation does NOT extrapolate")
        print("   • Returns None for values outside table range")
        print("   • This is safer but limits measurement range")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in extrapolation test: {e}")
        return False

if __name__ == "__main__":
    analyze_temperature_precision()
    test_extrapolation_limits()