import mysql.connector
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# Define CSV file paths
csv_file_paths = {
    'stocks':  r'D:\APC\Combined_Data.csv',
    'volatile_stocks': r'D:\APC\Top_10_Vol_Stocks.csv',
    'top_performing_stocks': r'D:\APC\Top_5_stocks.csv',
    'sector_performance':  r'D:\APC\SectorWisePerformance.csv',
    'correlation_matrix': r'D:\APC\Correlation_Matrix.csv',
    'top_gainers_losers': r'D:\APC\Top_Gainers_Losers_Monthwise.csv',
    'green_red_stocks': r'D:\Myproject2\TopGainNLoss_Data.csv',
    'market_summary' : r"D:\Myproject2\MarketSummary.csv"
}

# MySQL setup
mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    port=3306,
    autocommit=True
)
mycursor = mydb.cursor(buffered=True)
mycursor.execute("CREATE DATABASE IF NOT EXISTS STOCKDATA")
mycursor.execute("USE STOCKDATA")

def create_table():
    for table_name, file_path in csv_file_paths.items():
        df = pd.read_csv(file_path)
        columns = [col.replace(" ", "_").replace("&", "_and_") for col in df.columns]
        column_definitions = ', '.join([f"`{col}` VARCHAR(255)" for col in columns])
        create_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({column_definitions})"
        try:
            mycursor.execute(create_query)
        except mysql.connector.Error as err:
            print(f"Error creating table {table_name}: {err}")

def load_data_to_mysql(csv_file_path, table_name):
    df = pd.read_csv(csv_file_path)
    columns = [col.strip().replace(" ", "_").replace("&", "_and_").replace("__", "_") for col in df.columns]
    df.columns = columns
    df = df.where(pd.notnull(df), None)
    placeholders = ', '.join(['%s'] * len(df.columns))
    sql = f"INSERT INTO `{table_name}` ({', '.join(df.columns)}) VALUES ({placeholders})"
    for _, row in df.iterrows():
        try:
            mycursor.execute(sql, tuple(row))
        except mysql.connector.Error:
            continue

def insert_all_data():
    for table_name, file_path in csv_file_paths.items():
        load_data_to_mysql(file_path, table_name)

def load_data_from_mysql(query):
    mycursor.execute(query)
    data = mycursor.fetchall()
    columns = [i[0] for i in mycursor.description]
    return pd.DataFrame(data, columns=columns)

#Market Summary
def market_summary():
    # Load the 'MarketSummary.csv' data
    df = pd.read_csv(r"D:\Myproject2\MarketSummary.csv")
    
    # Since the CSV contains summarized data, directly retrieve the values
    green_stocks = df['No of Green Stocks'].values[0]  # Get the first value from the column
    red_stocks = df['No of Red Stocks'].values[0]  # Get the first value from the column
    avg_price = df['average_price'].values[0]  # Get the first value from the column
    avg_volume = df['average_volume'].values[0]  # Get the first value from the column

    # Display metrics in columns
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Average Price", f"₹{avg_price:.2f}")
        st.metric("Average Volume", f"{avg_volume:,.0f}")

    with col2:
        st.subheader("Green vs Red Stocks")
        labels = ['Green', 'Red']
        values = [green_stocks, red_stocks]
        colors = ['#2ecc71', '#e74c3c']

        fig, ax = plt.subplots()
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        st.pyplot(fig)

# Function to plot top 10 volatile stocks (bar chart with stock tickers on x-axis and volatility on y-axis)
def top_10_volatile_stocks():
    # Query to fetch all volatility data, ensuring it returns 10 rows
    df = load_data_from_mysql("SELECT * FROM volatile_stocks ORDER BY Volatility DESC LIMIT 10")
    
    # Check if data is loaded correctly
    if not df.empty:
        # Sort the dataframe by volatility in descending order
        df_sorted = df.sort_values('Volatility', ascending=False)

        # Visualizing top 10 volatile stocks with stock ticker on x-axis and volatility on y-axis
        
        # Creating the bar chart with Plotly
        fig = px.bar(df_sorted, 
                     x='Ticker', 
                     y='Volatility', 
                     title='Top 10 Most Volatile Stocks',
                     labels={'Ticker': 'Stock Ticker', 'Volatility': 'Volatility (Standard Deviation)'},
                     color='Volatility', 
                     color_continuous_scale='Viridis')

        # Rotate x-axis labels for better readability
        fig.update_layout(xaxis_tickangle=-45)
        
        # Show plot
        st.plotly_chart(fig)


def top_5_performing_stocks():
    # Load top 5 performing stocks from the CSV file directly into a DataFrame
    df = pd.read_csv(r'D:\APC\Top_5_stocks.csv')

    if not df.empty:
        # Assuming the structure of the CSV file is correct and contains relevant data
        # Create a horizontal bar chart using Plotly
        fig_bar = go.Figure(go.Bar(
            x=df['Cumulative_Return'],
            y=df['Ticker'],
            orientation='h',
            marker=dict(
                color=df['Cumulative_Return'],  # Color by Cumulative Return
                colorscale='Viridis',  # Apply the Viridis color scale
                showscale=True  # Show the color scale legend
            )
        ))

        # Customize the layout of the bar chart
        fig_bar.update_layout(
            title='Top 5 Performing Stocks by Cumulative Return',
            xaxis_title='Cumulative Return',
            yaxis_title='Ticker'
        )

        # Display the plot in Streamlit
        st.plotly_chart(fig_bar)
          
        
def stock_price_correlation_heatmap():
    df = load_data_from_mysql("SELECT * FROM stocks")
    df['date'] = pd.to_datetime(df['date'])

    # Handling duplicates by removing or aggregating data before pivot
    df = df.drop_duplicates(subset=['date', 'Ticker'])

    # Alternatively, aggregate the data if necessary (e.g., by taking the mean)
    # df = df.groupby(['date', 'Ticker'], as_index=False)['close'].mean()

    df_pivot = df.pivot(index='date', columns='Ticker', values='close')
    correlation_matrix = df_pivot.corr()
    plt.figure(figsize=(30, 30))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', linewidths=0.5)
    plt.title('Stock Price Correlation Heatmap')
    st.pyplot(plt)

def top_gainers_and_losers():
    df = load_data_from_mysql("SELECT * FROM top_gainers_losers")
    if df.empty:
        return
    available_months = df['Month'].unique()
    selected_month = st.selectbox("Select Month", sorted(available_months, reverse=True))
    month_data = df[df['Month'] == selected_month]
    gainers = month_data[month_data['Type'] == 'Gainer'].sort_values(by='monthly_return', ascending=False)
    losers = month_data[month_data['Type'] == 'Loser'].sort_values(by='monthly_return')
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 5 Gainers")
        st.dataframe(gainers.reset_index(drop=True))
        st.bar_chart(gainers.set_index('Ticker')['monthly_return'])
    with col2:
        st.subheader("Top 5 Losers")
        st.dataframe(losers.reset_index(drop=True))
        st.bar_chart(losers.set_index('Ticker')['monthly_return'])

def sector_wise_performance():
    df = load_data_from_mysql("SELECT * FROM sector_performance")
    df['avg_1_year_return'] = df['avg_1_year_return'].astype(float)
    st.subheader("Sector-Wise Performance")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(x='sector', y='avg_1_year_return', data=df.sort_values('avg_1_year_return', ascending=False), palette='coolwarm')
    plt.xticks(rotation=45)
    plt.ylabel('Average 1-Year Return (%)')
    st.pyplot(fig)

def top_10_green_red_stocks():
    green_df = pd.read_csv(r"D:\Myproject2\Top_10_Green_Stocks.csv")
    red_df = pd.read_csv(r"D:\Myproject2\Top_10_Red_Stocks.csv")

    green_df['Yearly Return Percentage'] = green_df['Yearly Return Percentage'].astype(float)
    red_df['Yearly Return Percentage'] = red_df['Yearly Return Percentage'].astype(float)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 10 Green Stocks")
        st.dataframe(green_df[['Ticker', 'Yearly Return Percentage']])
        st.bar_chart(green_df.set_index('Ticker')['Yearly Return Percentage'])

    with col2:
        st.subheader("Top 10 Red Stocks")
        st.dataframe(red_df[['Ticker', 'Yearly Return Percentage']])
        st.bar_chart(red_df.set_index('Ticker')['Yearly Return Percentage'])

# Main App
def main():
    st.set_page_config(page_title="Stock Performance Dashboard", layout="wide")
    st.title("\U0001F4C8 Nifty 50 Stock Market Dashboard")

    st.sidebar.title("\U0001F527 Dashboard Controls")
    page = st.sidebar.selectbox("\U0001F4C1 Select Section", [
        "Market Summary",
        "Top 10 Volatile Stocks",
        "Top 5 Performing Stocks",
        "Stock Price Correlation Heatmap",
        "Monthly Top Gainers & Losers",
        "Sector-Wise Performance",
        "Top 10 Green & Red Stocks"
    ])

    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

    if st.sidebar.button("\U0001F4E5 Load Data into MySQL") and not st.session_state.data_loaded:
        create_table()
        insert_all_data()
        st.session_state.data_loaded = True
        st.sidebar.success("Data inserted successfully!")
    elif st.session_state.data_loaded:
        st.sidebar.info("\u2705 Data already loaded in session.")

    if page == "Market Summary":
        st.header("\U0001F4CC Market Summary")
        market_summary()
    elif page == "Top 10 Volatile Stocks":
        st.header("\U0001F4C9 Top 10 Most Volatile Stocks")
        top_10_volatile_stocks()
    elif page == "Top 5 Performing Stocks":
        st.header("\U0001F4C8 Top 5 Performing Stocks")
        top_5_performing_stocks()
    elif page == "Stock Price Correlation Heatmap":
        st.header("\U0001F517 Stock Price Correlation Heatmap")
        stock_price_correlation_heatmap()
    elif page == "Monthly Top Gainers & Losers":
        st.header("\U0001F4C6 Monthly Gainers and Losers")
        top_gainers_and_losers()
    elif page == "Sector-Wise Performance":
        st.header("\U0001F3E2 Sector-Wise Performance")
        sector_wise_performance()
    elif page == "Top 10 Green & Red Stocks":
        st.header("\U0001F4B9 Yearly Return Leaders & Laggards")
        top_10_green_red_stocks()

if __name__ == '__main__':
    main()
