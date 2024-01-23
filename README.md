# Pumping Test of Water Wells
Practical application for interpreting pumping tests on water wells, based on the ICRC's guidelines "Technical Review - Practical Guidelines for Test Pumping in Water Wells", 2011.

The following tests are considered:
- Step drawdown test
- Constant-rate test
- Recovery test

### [Live demo](https://plosi.shinyapps.io/pumpingtest/) on shinyapps.io

## How to use the app
0. Download the template files.
1. Select the type of pumping test that you want to analyse.
2. Load the file with your data. Please note that at the moment the only format accepted is 
".csv" (separator: comma) with two columns named "time_min" and "level_m": the first column represents 
the elapsed time in minutes, the second one represents the water level measured in meters from the 
datum.
3. Fill in the "General Information" (optional) and the "Data Input" fields. Please note that the 
borehole name is used in the title of the charts.
4. Explore the "Data Preview" tab. If you are running the step-drawdown test interpretation, 
check the chart in this session to see if the steps are correctly timed.
5. Check the "Analysis" tab to view the results. If you are running the constant-rate or recovery 
test interpretation, use the slider to get the best fit before accepting the results.
            
## Future improvements (work in progress...)
- Make the charts interactive (use plotly).
- Add a "Create Report" button to print a pdf report with the test results.
- Load handwritten forms using the phone/tablet camera.
- Use AI algorithms to improve accuracy of the results by comparing the curves with similar cases and 
providing additional insights on the borehole's efficiency and aquifer's characteristics.
- Allow also ".xls/xlsx" files.
- Allow for different units of measurements.
- Allow for no specific file format, i.e. let the user select which columns correspond to the elapsed time 
and water levels when they load a new data file.
- Allow the user to import a single file for constant-rate and recovery test.
