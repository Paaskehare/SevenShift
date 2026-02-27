from django.db import models


class Make(models.Model):
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    founded = models.PositiveIntegerField(blank=True, null=True, help_text="Year founded")
    logo_url = models.URLField(blank=True)
    data_id = models.IntegerField(db_index=True, null=True, help_text="auto-data.net brand ID")

    class Meta:
        ordering = ['name']
        verbose_name = 'Make'
        verbose_name_plural = 'Makes'

    def __str__(self):
        return self.name


class CarModel(models.Model):
    make = models.ForeignKey(Make, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    data_id = models.IntegerField(db_index=True, null=True, help_text="auto-data.net model ID")

    class Meta:
        ordering = ['make', 'name']
        verbose_name = 'Car Model'
        verbose_name_plural = 'Car Models'
        unique_together = [('make', 'name')]

    def __str__(self):
        return f"{self.make.name} {self.name}"


class Generation(models.Model):
    car_model = models.ForeignKey(CarModel, on_delete=models.CASCADE, related_name='generations')
    name = models.CharField(max_length=50, blank=True, null=True, help_text="Generation code/name, e.g. 'E90', 'Mk IV'")
    production_start = models.PositiveIntegerField(blank=True, null=True, help_text="Year")
    production_end = models.PositiveIntegerField(blank=True, null=True, help_text="Year")
    data_id = models.IntegerField(db_index=True, null=True, help_text="auto-data.net submodel ID")

    class Meta:
        ordering = ['car_model', 'production_start']
        verbose_name = 'Generation'
        verbose_name_plural = 'Generations'
        unique_together = [('car_model', 'name')]

    def __str__(self):
        label = f"{self.car_model.make}"
        if self.name:
            label += f" {self.name}"
        if self.production_start:
            end = self.production_end or 'present'
            label += f" ({self.production_start}–{end})"
        return label


class Variant(models.Model):
    MOTOR_LOCATION_CHOICES = [
        ('front', 'Front'),
        ('rear', 'Rear'),
        ('mid', 'Mid'),
        ('dual', 'Dual (Front + Rear)'),
    ]

    CHARGING_PORT_CHOICES = [
        ('type1', 'Type 1'),
        ('type2', 'Type 2'),
        ('ccs', 'CCS'),
        ('chademo', 'CHAdeMO'),
        ('gb_t', 'GB/T'),
    ]

    generation = models.ForeignKey(Generation, on_delete=models.CASCADE, related_name='variants')
    variant = models.CharField(max_length=100, blank=True, null=True, help_text="Trim/variant name")
    modification = models.CharField(max_length=150, blank=True, null=True, help_text="Engine / modification descriptor")
    body_type = models.CharField(max_length=100, blank=True, null=True)
    seats = models.PositiveSmallIntegerField(blank=True, null=True)
    doors = models.PositiveSmallIntegerField(blank=True, null=True)

    # Engine / ICE
    fuel_type = models.CharField(max_length=100, blank=True, null=True)
    engine_displacement_cc = models.PositiveIntegerField(blank=True, null=True)
    engine_cylinders = models.PositiveSmallIntegerField(blank=True, null=True)
    power_hp = models.PositiveSmallIntegerField(blank=True, null=True, help_text="hp")
    power_kw = models.PositiveSmallIntegerField(blank=True, null=True, help_text="kW")
    torque_nm = models.PositiveIntegerField(blank=True, null=True, help_text="Nm")
    transmission = models.CharField(max_length=50, blank=True, null=True)
    number_of_gears = models.PositiveSmallIntegerField(blank=True, null=True)
    drive = models.CharField(max_length=20, blank=True, null=True)

    # Performance
    acceleration_0_100 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Seconds (0–100 km/h)")
    top_speed_kmh = models.PositiveIntegerField(blank=True, null=True, help_text="km/h")

    # ICE economy
    fuel_consumption_l100km = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="L/100km combined (WLTP)")
    fuel_consumption_urban_l100km = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="L/100km urban")
    fuel_consumption_extra_urban_l100km = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="L/100km extra-urban")
    fuel_tank_l = models.PositiveSmallIntegerField(blank=True, null=True, help_text="L")
    co2_g_km = models.PositiveSmallIntegerField(blank=True, null=True, help_text="g/km")

    # Battery & Electric
    gross_battery_capacity = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="kWh")
    all_electric_range = models.PositiveIntegerField(blank=True, null=True, help_text="km")
    average_energy_consumption = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="kWh/100km (WLTP)")
    charging_ports = models.CharField(max_length=50, choices=CHARGING_PORT_CHOICES, blank=True, null=True)
    electric_motor_type = models.CharField(max_length=100, blank=True, null=True)
    electric_motor_location = models.CharField(max_length=50, choices=MOTOR_LOCATION_CHOICES, blank=True, null=True)
    electric_motor_code = models.CharField(max_length=100, blank=True, null=True)
    electric_platform = models.CharField(max_length=100, blank=True, null=True)

    # Dimensions & weight
    length_mm = models.PositiveIntegerField(blank=True, null=True, help_text="mm")
    width_mm = models.PositiveIntegerField(blank=True, null=True, help_text="mm")
    height_mm = models.PositiveIntegerField(blank=True, null=True, help_text="mm")
    wheelbase_mm = models.PositiveIntegerField(blank=True, null=True, help_text="mm")
    curb_weight_kg = models.PositiveSmallIntegerField(blank=True, null=True, help_text="kg")
    max_weight_kg = models.PositiveIntegerField(blank=True, null=True, help_text="kg (GVW)")
    max_load_kg = models.PositiveIntegerField(blank=True, null=True, help_text="kg")
    trunk_volume_l = models.PositiveSmallIntegerField(blank=True, null=True, help_text="L")

    # Importer bookkeeping
    data_id = models.IntegerField(db_index=True, null=True, help_text="auto-data.net vehicle ID")
    scraped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['generation', 'variant']
        verbose_name = 'Variant'
        verbose_name_plural = 'Variants'

    def __str__(self):
        parts = [str(self.generation)]
        if self.variant:
            parts.append(self.variant)
        if self.modification:
            parts.append(f'({self.modification})')
        return ' '.join(parts)

    @property
    def car_model(self):
        return self.generation.car_model

    @property
    def display_name(self):
        return str(self)
