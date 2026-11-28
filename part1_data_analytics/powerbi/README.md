# Power BI deliverable

`Traffic_Data_Analysis.pbix` is the native dashboard file. `traffic_dashboard_data.csv` is a prepared 48,204-row extract containing 17 exact duplicate rows. The PBIX removes those duplicates before reporting, leaving 48,187 observations in the final model. `Traffic_Power_Query.m` contains repeatable transformations for the original nine-column raw CSV; its source path is a placeholder and must be changed to the location of that raw CSV before refreshing. The dashboard specification and build steps define the required visuals, aggregations, filters, slicers, and units.

Open the PBIX in Power BI Desktop to inspect it. The raw CSV is not included in this checkout. Follow `powerbi_build_steps.md` for the expected visuals, calculations, and refresh procedure.

The query specifies the nine source-column data types, standardizes blank holiday entries to the explicit `None` no-holiday category, filters null timestamps and negative traffic, derives date/year/hour and Celsius temperature, and creates mutually exclusive traffic categories: `<4500` Low, `4500–5500` Medium (inclusive endpoints), and `>5500` High. It flags zero-K temperatures and extreme rainfall, retains their traffic observations, and removes exact duplicate rows across the transformed table.
