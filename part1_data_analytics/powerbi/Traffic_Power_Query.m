let
    // Replace this path with the location of the supplied Metro CSV.
    Source = Csv.Document(
        File.Contents("C:\path\to\Metro_Interstate_Traffic_Volume.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(
        Headers,
        {
            {"holiday", type text},
            {"temp", type number},
            {"rain_1h", type number},
            {"snow_1h", type number},
            {"clouds_all", Int64.Type},
            {"weather_main", type text},
            {"weather_description", type text},
            {"date_time", type datetime},
            {"traffic_volume", Int64.Type}
        }
    ),
    HolidayNullsToNoHoliday = Table.ReplaceValue(Typed, null, "None", Replacer.ReplaceValue, {"holiday"}),
    HolidayBlanksToNoHoliday = Table.ReplaceValue(HolidayNullsToNoHoliday, "", "None", Replacer.ReplaceValue, {"holiday"}),
    AddDate = Table.AddColumn(HolidayBlanksToNoHoliday, "date", each Date.From([date_time]), type date),
    AddYear = Table.AddColumn(AddDate, "year", each Date.Year([date_time]), Int64.Type),
    AddHour = Table.AddColumn(AddYear, "hour", each Time.Hour(DateTime.Time([date_time])), Int64.Type),
    AddTemperatureC = Table.AddColumn(AddHour, "temp_c", each [temp] - 273.15, type number),
    AddTrafficCategory = Table.AddColumn(
        AddTemperatureC,
        "traffic_category",
        each if [traffic_volume] < 4500 then "Low"
             else if [traffic_volume] <= 5500 then "Medium"
             else "High",
        type text
    ),
    FilteredValidRows = Table.SelectRows(
        AddTrafficCategory,
        each [date_time] <> null and [traffic_volume] >= 0
    ),
    FlagZeroKelvin = Table.AddColumn(
        FilteredValidRows,
        "temp_zero_kelvin_flag",
        each [temp] <= 0,
        type logical
    ),
    FlagExtremeRain = Table.AddColumn(
        FlagZeroKelvin,
        "rain_above_9000_mm_flag",
        each [rain_1h] > 9000,
        type logical
    ),
    RemovedDuplicates = Table.Distinct(FlagExtremeRain)
in
    RemovedDuplicates
