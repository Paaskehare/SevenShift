from datetime import date

# date | battery deduction dkk/kwh | battery deduction wltp co2 emission g/km | battery deduction max kwh
BATTERY_DEDUCTIONS = (
    (date(2020, 12, 18), -1700.00, 50, 45),
    (date(2020, 1, 1), -1700.00, 50, 45),
    (date(2022, 1, 1), -1300.00, 50, 45),
    (date(2023, 1, 1), -900.00, 50, 45),
    (date(2024, 1, 1), -500.00, 50, 45),
    (date(2025, 1, 1), 0.00, 50, 0),
)

# date | first limit | first rate | second limit | second rate | third limit | third rate

VAN_TAX_VALUE_BRACKETS = (
    (date(2021,1,1), 75000, 0.0, None, 0.5),
    (date(2022,1,1), 75900, 0.0, None, 0.5),
    (date(2023,1,1), 78100, 0.0, None, 0.5),
    (date(2024,1,1), 80900, 0.0, None, 0.5),
    (date(2025,1,1), 84000, 0.0, None, 0.5),
)

TAX_VALUE_BRACKETS = (
    (date(2008,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2009,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2010,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2011,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2012,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2013,1,1), 79000, 1.050, None, 1.800, None, None),
	(date(2014,1,1), 80500, 1.050, None, 1.800, None, None),
	(date(2015,1,1), 81700, 1.050, None, 1.800, None, None),
	(date(2015,11,20), 81700, 1.050, None, 1.500, None, None),
	(date(2016,1,1), 82200, 1.050, None, 1.500, None, None),
	(date(2016,11,22), 104300, 1.050, None, 1.500, None, None),
	(date(2017,1,1), 106600, 1.050, None, 1.500, None, None),
	(date(2017,10,3), 185100, 0.850, None, 1.500, None, None),
	(date(2018,1,1), 189200, 0.850, None, 1.500, None, None),
	(date(2019,1,1), 193400, 0.850, None, 1.500, None, None),
	(date(2020,12,18), 63600, 0.250, 197700, 0.850, None, 1.500),
	(date(2021,1,1), 65000, 0.250, 202200, 0.850, None, 1.500),
	(date(2022,1,1), 65800, 0.250, 204600, 0.850, None, 1.500),
	(date(2023,1,1), 67800, 0.250, 210600, 0.850, None, 1.500),
	(date(2024,1,1), 70200, 0.250, 218100, 0.850, None, 1.500),
	(date(2025,1,1), 72900, 0.250, 226500, 0.850, None, 1.500),
    # estimates from 2024 ..
	(date(2026,1,1), 73013, 0.250, 226793, 0.850, None, 1.500),
	(date(2027,1,1), 74839, 0.250, 232463, 0.850, None, 1.500),
	(date(2028,1,1), 76709, 0.250, 238275, 0.850, None, 1.500),
	(date(2029,1,1), 78627, 0.250, 244231, 0.850, None, 1.500),
	(date(2030,1,1), 80593, 0.250, 250337, 0.850, None, 1.500),
	(date(2031,1,1), 82608, 0.250, 256596, 0.850, None, 1.500),
	(date(2032,1,1), 84673, 0.250, 263011, 0.850, None, 1.500),
	(date(2033,1,1), 86790, 0.250, 269586, 0.850, None, 1.500),
	(date(2034,1,1), 88959, 0.250, 276325, 0.850, None, 1.500),
	(date(2035,1,1), 91183, 0.250, 283234, 0.850, None, 1.500),
)

'''
https://www.skm.dk/skattetal/satser/satser-og-beloebsgraenser-i-lovgivningen/gaeldende-satser-for-registreringsafgiften/
Grænser:
(fra og med den 1. januar 2022 nedsættes grænseværdierne med 3,3 pct.-point årligt i hvert af årene 2022-2025 og med 1,1 pct.-point årligt i hvert af årene 2026-2030).

Lav sats af de første 125 g CO2 pr. km. 
Mellem sats af de næste 35 g CO2 pr. km

Høj sats af resten

2021: 121 g CO2 pr. km, 34 g CO2 pr. km
2022: 117 g CO2 pr. km 33 g CO2 pr. km
'''

# date | first limit | first rate | second limit | second rate | third limit | third rate
CO2_EMISSION_FEE_BRACKETS = (
	(date(2020,12,18), 125, 245, 160, 489, None, 929),
    (date(2021,1,1), 125, 250, 160, 500, None, 950),
	(date(2022,1,1), 121, 253, 155, 506, None, 961),
	(date(2023,1,1), 117, 261, 150, 521, None, 990),
	(date(2024,1,1), 113, 270, 145, 539, None, 1024),
	(date(2025,1,1), 109, 280, 139, 560, None, 1064),
)

# date | standard deduction | low co2 emission deduction limit in grams per km | low co2 emission deduction | no emission deduction limit in grams | no emission deduction
CO2_LOW_EMISSION_DEDUCTIONS = (
	(date(2020,12,18), -21200.00, 50, -50000.00, 0, -170000.00),
    (date(2021,1,1), -21700.00, 50, -50000.00, 0, -170000.00),
	(date(2022,1,1), -21700.00, 50, -48750.00, 0, -167500.00),
	(date(2023,1,1), -22600.00, 50, -47500.00, 0, -165000.00),
	(date(2024,1,1), -23400.00, 50, -46250.00, 0, -162500.00),
	(date(2024,2,1), -23400.00, 50, -46250.00, 0, -165500.00),
	(date(2025,1,1), -24300.00, 50, -45000.00, 0, -165500.00),
    # estimates from 2024
	(date(2026,1,1), -24338.00, 50, -43000.00, 0, -155400.00),
	(date(2027,1,1), -24946.00, 50, -41000.00, 0, -150800.00),
	(date(2028,1,1), -25570.00, 50, -39000.00, 0, -146200.00),
	(date(2029,1,1), -26209.00, 50, -37000.00, 0, -141600.00),
	(date(2030,1,1), -26864.00, 50, -35000.00, 0, -137000.00),
)


VAN_CO2_LOW_EMISSION_DEDUCTIONS = (
    (date(2023,1,1), -31200.00, 50, -47500.00, 0, -77500.00),
    (date(2024,1,1), -32200.00, 50, -46250.00, 0, -77500.00),
	(date(2024,2,1), -32200.00, 50, -46250.00, 0, -77500.00),
	(date(2025,1,1), -33600.00, 50, -45000.00, 0, -77500.00),
	#(date(2026,1,1), -32200.00, 50, -45000.00, 0, -73000.00),
)

# date | first limit (WLTP g/km) | first rate (PCT) | second_limit (WLTP g/km) | second_rate (PCT)
VAN_GRADUAL_REGISTRATION_FEE_APPLICATION_BRACKETS = (
    (date(2021,1,1), 0, 0.40, 50, 0.45),
    (date(2022,1,1), 0, 0.40, 50, 0.50),
	(date(2023,1,1), 0, 0.40, 50, 0.55),
	(date(2024,1,1), 0, 0.40, 50, 0.60),
	(date(2025,1,1), 0, 0.40, 50, 0.65),
)

# date | first limit (WLTP g/km) | first rate (PCT) | second_limit (WLTP g/km) | second_rate (PCT)
GRADUAL_REGISTRATION_FEE_APPLICATION_BRACKETS = (
	(date(2020,12,18), 0, 0.40, 50, 0.45),
	(date(2022,1,1), 0, 0.40, 50, 0.50),
	(date(2023,1,1), 0, 0.40, 50, 0.55),
	(date(2024,1,1), 0, 0.40, 50, 0.60),
	(date(2025,1,1), 0, 0.40, 50, 0.65),
	(date(2026,1,1), 0, 0.48, 50, 0.68),
	(date(2027,1,1), 0, 0.56, 50, 0.71),
	(date(2028,1,1), 0, 0.64, 50, 0.74),
	(date(2029,1,1), 0, 0.72, 50, 0.77),
	(date(2030,1,1), 0, 0.80, 50, 0.80),
	(date(2031,1,1), 0, 0.84, 50, 0.84),
	(date(2032,1,1), 0, 0.88, 50, 0.88),
	(date(2033,1,1), 0, 0.92, 50, 0.92),
	(date(2034,1,1), 0, 0.96, 50, 0.96),
	(date(2035,1,1), 0, 1.00, 50, 1.00),
)

DEPRECIATION_MINIMUM_IN_MONTHS = 48
DEPRECIATION_MINIMUM_IN_KM = 2000
MINIMUM_REGISTRATION_FEE = 0.00
MINIMUM_BASIS_TAXATION_AMOUNT = 160000.00

# Proportional registration tax depreciation rates (forholdsmæssig registreringsafgift)
# Monthly value-loss fractions per SKAT (Registreringsafgiftsloven §13)
REG_TAX_BAND1_RATE = 0.02   # months 0–3:  2 % / month
REG_TAX_BAND2_RATE = 0.01   # months 3–36: 2 % / month (>= 36 months: drops to band3)
REG_TAX_BAND3_RATE = 0.005   # months 36+:  1 % / month

VAN_MAX_REGISTRATION_FEE = 47000

SALES_ADVERT_DEDUCTION_PCT = -0.050
SALES_PREPARATION_DEDUCTION_PCT = -0.030
SALES_PREPARATION_DEDUCTION_LIMIT = -8000.00
LICENSE_PLATE_COSTS = 1180.00

# https://www.retsinformation.dk/eli/lta/2021/1147#P3

# for cars with first registration before 30. juni 2021

PERIOD_TAX_CO2_DATE = date(2021, 7, 1)

PETROL_BASE_VALUES = (
    # from value, first registration in DK before 2017, first registration in DK after 2017
    (50.0, 330, 330),
    (44.4, 330, 370),
    (40.0, 330, 390),
    (36.4, 330, 410),
    (33.3, 330, 430),
    (28.6, 330, 460),
    (25.0, 330, 500),
    (22.2, 330, 540),
    (20.0, 330, 580),
    (18.2, 640, 890),
    (16.7, 940, 1190),
    (15.4, 1260, 1510),
    (14.3, 1570, 1820),
    (13.3, 1870, 2120),
    (12.5, 2180, 2430),
    (11.8, 2480, 2730),
    (11.1, 2790, 3040),
    (10.5, 3100, 3350),
    (10.0, 3410, 3660),
    (9.1, 4010, 4260),
    (8.3, 4650, 4900),
    (7.7, 5260, 5510),
    (7.1, 5870, 6120),
    (6.7, 6480, 6730),
    (6.3, 7110, 7360),
    (5.9, 7720, 7970),
    (5.6, 8330, 8580),
    (5.3, 8970, 9220),
    (5.0, 9580, 9830),
    (4.8, 10190, 10440),
    (4.5, 10800, 11050),
    (0.0, 11430, 11680),
)

DIESEL_BASE_VALUES = (
    # from value, value for missing data, first registration in DK before 2017, first registration in DK after 2017, additional tax
    (56.3, None, 330, 130),
    (50.0, None, 370, 130),
    (45.0, None, 390, 130),
    (41.0, None, 410, 130),
    (37.6, None, 430, 130),
    (32.1, None, 460, 130),
    (28.1, None, 500, 610),
    (25.0, None, 540, 1090),
    (22.5, 330, 580, 1180),
    (20.5, 640, 890, 1300),
    (18.8, 940, 1190, 1400),
    (17.3, 1260, 1510, 1510),
    (16.1, 1570, 1820, 1620),
    (15.0, 1870, 2120, 1740),
    (14.1, 2180, 2430, 1870),
    (13.2, 2480, 2730, 1990),
    (12.5, 2790, 3040, 2120),
    (11.9, 3100, 3350, 2220),
    (11.3, 3410, 3660, 2330),
    (10.2, 4010, 4260, 2580),
    (9.4, 4650, 4900, 2790),
    (8.7, 5260, 5510, 3010),
    (8.1, 5870, 6120, 3270),
    (7.5, 6480, 6730, 3460),
    (7.0, 7110, 7360, 3680),
    (6.6, 7720, 7970, 3950),
    (6.2, 8330, 8580, 4160),
    (5.9, 8970, 9220, 4380),
    (5.6, 9580, 9830, 4640),
    (5.4, 10190, 10440, 4870),
    (5.1, 10800, 11050, 5170),
    (0.0, 11430, 11680, 5410),
)

# Den 15. februar 2021 forhøjes de i stk. 1 under B angivne beløb for udligningsafgift med 20,7 pct. 
DIESEL_COMPENSATION_TAX_PERCENTAGE = 0.207

# for cars with first registration after 1. juli 2021
CO2_EMISSION_BASE_VALUES = (
    (645, 11680, 6530),
    (605, 11050, 6240),
    (581, 10440, 5880),
    (548, 9830, 5600),
    (519, 9220, 5290),
    (492, 8580, 5020),
    (461, 7970, 4770),
    (433, 7360, 4440),
    (409, 6730, 4180),
    (377, 6120, 3950),
    (350, 5510, 3630),
    (319, 4900, 3370),
    (290, 4260, 3110),
    (277, 3660, 2810),
    (262, 3350, 2680),
    (246, 3040, 2560),
    (232, 2730, 2400),
    (218, 2430, 2260),
    (203, 2120, 2100),
    (189, 1820, 1960),
    (174, 1510, 1820),
    (160, 1190, 1690),
    (145, 890, 1570),
    (131, 580, 1420),
    (116, 540, 1320),
    (102, 500, 740),
    (87, 460, 160),
    (80, 430, 160),
    (73, 410, 160),
    (65, 390, 160),
    (58, 370, 160),
    (0, 330, 160),
)

PERIOD_TAX_GRADUAL_INCREASE = (
	(date(2022,1,1), 0.03,),
	(date(2023,1,1), 0.097,),
	(date(2024,1,1), 0.168,),
	(date(2025,1,1), 0.244,),
	(date(2026,1,1), 0.369,),
)

# no matter the car value, you will always get taxed atleast this amount
COMPANY_CAR_TAXATION_HARD_LIMIT = 160000
COMPANY_CAR_TAXATION_LOWER_LIMIT = 300000

# under 300k, over 300k, "miljøtillæg"
COMPANY_CAR_TAXATION = (
    (date(1970,1,1), 0.25,  0.20,  1.5),
	(date(2021,7,1), 0.245, 0.205, 2.5),
    (date(2022,1,1), 0.24,  0.21,  3.5),
    (date(2023,1,1), 0.235, 0.215, 4.5),
    (date(2024,1,1), 0.23,  0.22,  6.0),
    (date(2025,1,1), 0.225, 0.225, 7.0),
)

def get_latest_date_row(arr, target_date):
    current = None
    for row in arr:
        row_date = row[0]
        if row_date <= target_date:
            current = row
        elif row_date > target_date:
            # since the list is ordered, just exit the loop if the date we encountered is larger
            break

    return current

def get_highest_value_row(arr, target_value):
    for row in arr:
        row_value = row[0]
        if int(target_value) >= int(row_value):
            return row