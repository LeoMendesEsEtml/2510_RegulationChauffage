
ADC_PARAMS_DB = {
    # Nom du profil : paramètres ADC associés
    "AF60":      {"ref_bank": 2, "idac_uA": 100, "gain": 4, "data_rate_sps": 20},
    "QAC32":     {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "PT1000":    {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NI1000_TK5000": {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NI1000_TK6180": {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NTC_1k_3528":   {"ref_bank": 2, "idac_uA": 100, "gain": 1, "data_rate_sps": 20},
    "KTY81_210":     {"ref_bank": 2, "idac_uA": 100, "gain": 4, "data_rate_sps": 20},
    "NTC_2k_3390":   {"ref_bank": 3, "idac_uA": 10,  "gain": 8, "data_rate_sps": 20},
    "NTC_2.2k_3528": {"ref_bank": 3, "idac_uA": 10,  "gain": 4, "data_rate_sps": 20},
    "NTC_10k_3977":  {"ref_bank": 3, "idac_uA": 10,  "gain": 1, "data_rate_sps": 20}
}

from dataclasses import dataclass
from math import exp, log

@dataclass
class SensorProfile:
    name: str
    kind: str          # "PTC" or "NTC"
    r0_ohm: float      # valeur à t0_c
    t0_c: float
    alpha_per_c: float = 0.0  # PTC
    A: float = 0.0            # NTC S-H (C=0 ici)
    B: float = 0.0
    C: float = 0.0
    rref_nom: float = 10_000  # Rref nominal du réseau

def _ptc_from_two_points(t1_c: float, r1_ohm: float, t2_c: float, r2_ohm: float):
    # Modèle linéaire R(T) = R0 * (1 + alpha * (T - 0))
    slope = (r2_ohm - r1_ohm) / (t2_c - t1_c)
    r0 = r1_ohm - slope * t1_c
    alpha = slope / r0
    return r0, alpha

def _ntc_sh_from_two_points(t1_c: float, r1_ohm: float, t2_c: float, r2_ohm: float):
    # Steinhart?Hart réduit: 1/T = A + B*ln(R), C = 0
    t1_k = t1_c + 273.15
    t2_k = t2_c + 273.15
    B = (1.0 / t1_k - 1.0 / t2_k) / (log(r1_ohm) - log(r2_ohm))
    A = 1.0 / t1_k - B * log(r1_ohm)
    # r0_ohm pris à 25 °C pour cohérence des NTC
    t0_k = 25.0 + 273.15
    ln_r25 = (1.0 / t0_k - A) / B
    r25 = exp(ln_r25)
    return A, B, 0.0, r25

# -------------------------
# Profils PTC
# Points utilisés: T1 = -15 °C, T2 = 40 °C
# -------------------------
_pt1000_r0, _pt1000_alpha = _ptc_from_two_points(-15.0, 942.0, 40.0, 1155.5)
_ni_tk5000_r0, _ni_tk5000_alpha = _ptc_from_two_points(-15.0, 935.0, 40.0, 1185.71)
_ni_tk6180_r0, _ni_tk6180_alpha = _ptc_from_two_points(-15.0, 919.0, 40.0, 1230.7)

# KTY81-210 est un PTC silicium (montre bien une pente +)
_kty81_r0, _kty81_alpha = _ptc_from_two_points(-15.0, 1423.0, 40.0, 2245.0)

# -------------------------
# Profils NTC
# Points utilisés: T1 = -15 °C, T2 = 40 °C
# -------------------------
_af60_A, _af60_B, _af60_C, _af60_r25 = _ntc_sh_from_two_points(-15.0, 2015.54, 40.0, 251.37)
_qac32_A, _qac32_B, _qac32_C, _qac32_r25 = _ntc_sh_from_two_points(-15.0, 653.0, 40.0, 525.0)
_ntc1k_A, _ntc1k_B, _ntc1k_C, _ntc1k_r25 = _ntc_sh_from_two_points(-15.0, 5855.0, 40.0, 1230.11)
_ntc2k_A, _ntc2k_B, _ntc2k_C, _ntc2k_r25 = _ntc_sh_from_two_points(-15.0, 11124.0, 40.0, 1168.06)
_ntc2r2k_A, _ntc2r2k_B, _ntc2r2k_C, _ntc2r2k_r25 = _ntc_sh_from_two_points(-15.0, 12881.0, 40.0, 1173.0)
_ntc10k_A, _ntc10k_B, _ntc10k_C, _ntc10k_r25 = _ntc_sh_from_two_points(-15.0, 72502.0, 40.0, 5320.0)

SENSOR_DB = {
    # PTC ? r0_ohm calculé à 0 °C ; alpha en [1/°C]
    "PT1000": SensorProfile(
        name="PT1000", kind="PTC",
        r0_ohm=_pt1000_r0, t0_c=0.0,
        alpha_per_c=_pt1000_alpha, rref_nom=10000.0
    ),
    "NI1000_TK5000": SensorProfile(
        name="Ni1000 TK5000", kind="PTC",
        r0_ohm=_ni_tk5000_r0, t0_c=0.0,
        alpha_per_c=_ni_tk5000_alpha, rref_nom=10000.0
    ),
    "NI1000_TK6180": SensorProfile(
        name="Ni1000 TK6180", kind="PTC",
        r0_ohm=_ni_tk6180_r0, t0_c=0.0,
        alpha_per_c=_ni_tk6180_alpha, rref_nom=10000.0
    ),
    "KTY81_210": SensorProfile(
        name="KTY81-210", kind="PTC",
        r0_ohm=_kty81_r0, t0_c=0.0,
        alpha_per_c=_kty81_alpha, rref_nom=10000.0
    ),
    # NTC ? Steinhart?Hart 2 paramètres (C = 0), r0_ohm à 25 °C
    "AF60": SensorProfile(
        name="De Dietrich AF60", kind="NTC",
        r0_ohm=_af60_r25, t0_c=25.0,
        A=_af60_A, B=_af60_B, C=_af60_C, rref_nom=10000.0
    ),
    "QAC32": SensorProfile(
        name="Siemens QAC32", kind="NTC",
        r0_ohm=_qac32_r25, t0_c=25.0,
        A=_qac32_A, B=_qac32_B, C=_qac32_C, rref_nom=10000.0
    ),
    "NTC_1k_3528": SensorProfile(
        name="NTC 1k 3528", kind="NTC",
        r0_ohm=_ntc1k_r25, t0_c=25.0,
        A=_ntc1k_A, B=_ntc1k_B, C=_ntc1k_C, rref_nom=10000.0
    ),
    "NTC_2k_3390": SensorProfile(
        name="NTC 2k 3390", kind="NTC",
        r0_ohm=_ntc2k_r25, t0_c=25.0,
        A=_ntc2k_A, B=_ntc2k_B, C=_ntc2k_C, rref_nom=10000.0
    ),
    "NTC_2.2k_3528": SensorProfile(
        name="NTC 2.2k 3528", kind="NTC",
        r0_ohm=_ntc2r2k_r25, t0_c=25.0,
        A=_ntc2r2k_A, B=_ntc2r2k_B, C=_ntc2r2k_C, rref_nom=10000.0
    ),
    "NTC_10k_3977": SensorProfile(
        name="NTC 10k 3977", kind="NTC",
        r0_ohm=_ntc10k_r25, t0_c=25.0,
        A=_ntc10k_A, B=_ntc10k_B, C=_ntc10k_C, rref_nom=10000.0
    ),
}

ADC_PARAMS_DB = {
    "AF60":      {"ref_bank": 2, "idac_uA": 100, "gain": 4, "data_rate_sps": 20},
    "QAC32":     {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "PT1000":    {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NI1000_TK5000": {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NI1000_TK6180": {"ref_bank": 2, "idac_uA": 100, "gain": 8, "data_rate_sps": 20},
    "NTC_1k_3528":   {"ref_bank": 2, "idac_uA": 100, "gain": 1, "data_rate_sps": 20},
    "KTY81_210":     {"ref_bank": 2, "idac_uA": 100, "gain": 4, "data_rate_sps": 20},
    "NTC_2k_3390":   {"ref_bank": 3, "idac_uA": 10,  "gain": 8, "data_rate_sps": 20},
    "NTC_2.2k_3528": {"ref_bank": 3, "idac_uA": 10,  "gain": 4, "data_rate_sps": 20},
    "NTC_10k_3977":  {"ref_bank": 3, "idac_uA": 10,  "gain": 1, "data_rate_sps": 20}
}

