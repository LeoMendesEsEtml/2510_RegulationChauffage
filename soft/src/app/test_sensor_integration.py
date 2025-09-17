# -*- coding: utf-8 -*-
# file: test_sensor_integration.py
"""
Test script to validate that all sensor profiles and tables are correctly integrated
for remote device deployment.
"""

def test_sensor_integration():
    """
    Test that all sensors in SENSOR_PROFILES have corresponding tables in SENSOR_TABLES
    and that the temperature conversion functions work correctly.
    """
    try:
        from app.sensor_profiles import SENSOR_PROFILES, SENSOR_TABLES
        from app.temperature_conversion import resistance_to_temperature_dynamic
        
        print("=== Testing Sensor Integration for Remote Device ===")
        
        # Check that all sensors in SENSOR_PROFILES have tables
        missing_tables = []
        for sensor_name in SENSOR_PROFILES.keys():
            if sensor_name not in SENSOR_TABLES:
                missing_tables.append(sensor_name)
        
        if missing_tables:
            print(f"❌ ERROR: Missing tables for sensors: {missing_tables}")
            return False
        else:
            print("✅ All sensors have corresponding tables")
        
        # Test temperature conversion for each sensor
        print("\n=== Testing Temperature Conversion ===")
        test_resistances = {
            "Ni1000 TK5000": 1103.0,    # Should be around 22°C
            "De Dietrich AF60": 1000.0,   # Should be around 3°C
            "PT1000": 1000.0,             # Should be 0°C
            "Siemens QAC32": 620.0,       # Should be 0°C
            "NTC 1k 3528": 2000.0,        # Should be around 8°C
            "KTY81-210": 1700.0,          # Should be around 5°C
        }
        
        all_tests_passed = True
        for sensor_name, test_resistance in test_resistances.items():
            try:
                temperature = resistance_to_temperature_dynamic(test_resistance, sensor_name)
                if temperature is not None:
                    print(f"✅ {sensor_name}: {test_resistance}Ω → {temperature:.2f}°C")
                else:
                    print(f"❌ {sensor_name}: {test_resistance}Ω → Temperature calculation failed")
                    all_tests_passed = False
            except Exception as e:
                print(f"❌ {sensor_name}: Error - {e}")
                all_tests_passed = False
        
        # Test edge cases - resistance outside table range
        print("\n=== Testing Edge Cases ===")
        try:
            # Test with resistance outside table range
            temp = resistance_to_temperature_dynamic(50000.0, "Ni1000 TK5000")  # Way too high
            if temp is None:
                print("✅ Out-of-range resistance correctly returns None")
            else:
                print(f"⚠️  Out-of-range resistance returned: {temp}°C (should be None)")
        except Exception as e:
            print(f"❌ Edge case test failed: {e}")
            all_tests_passed = False
        
        # Test with non-existent sensor
        try:
            temp = resistance_to_temperature_dynamic(1000.0, "NonExistentSensor")
            print("❌ Non-existent sensor should raise ValueError")
            all_tests_passed = False
        except ValueError:
            print("✅ Non-existent sensor correctly raises ValueError")
        except Exception as e:
            print(f"❌ Unexpected error for non-existent sensor: {e}")
            all_tests_passed = False
        
        print(f"\n=== Summary ===")
        if all_tests_passed:
            print("✅ ALL TESTS PASSED - System ready for remote deployment")
            return True
        else:
            print("❌ SOME TESTS FAILED - Fix issues before remote deployment")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Check that all modules are properly structured for remote device")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_sensor_integration()