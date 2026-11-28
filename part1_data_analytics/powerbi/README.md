# Power BI deliverable

`Traffic_Data_Analysis.pbix` is the native dashboard file. `traffic_dashboard_data.csv` is a prepared 48,204-row data extract. `Traffic_Power_Query.m` contains repeatable transformations for the original nine-column CSV; its source path is a placeholder and must be changed to the location of that raw CSV before refreshing with the query. The dashboard specification and build steps define the required visuals, aggregations, filters, slicers, and units.

Open the PBIX in Power BI Desktop to inspect it. The raw CSV is not included in this checkout. Follow `powerbi_build_steps.md` for the expected visuals, calculations, and refresh procedure.

The query specifies the nine source-column data types, replaces missing holiday entries with the empty no-holiday category, derives date/year/hour and Celsius temperature, and creates mutually exclusive traffic categories: `<4500` Low, `4500–5500` Medium (inclusive endpoints), and `>5500` High. It also flags zero-K temperatures and extreme rainfall for review.
