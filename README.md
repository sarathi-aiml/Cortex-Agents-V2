
# Cortex Agents V2

This project demonstrates how to quickly build complete **Cortex Agents** in Snowflake that combine **structured data analysis**, **unstructured conversation search**, **external API calls**, and **automated workflows**.

![Cortex Agents Diagram](https://github.com/sarathi-aiml/Cortex-Agents-V2/blob/main/images/Cortex-Agents.png?raw=true)



By following the steps in this repository, you will learn how to:

- Create Cortex Agents powered by **Cortex Analyst** for structured sales data.
- Create Cortex Agents powered by **Cortex Search** for unstructured sales conversation data.
- Develop User Defined Functions (UDFs) to call **external stock APIs**.
- Orchestrate custom Agents that use your preferred language model.
- Extend Agents with **custom tools**, including an email-sending stored procedure to deliver reports directly.

The goal is to showcase how easy it is to create a complete **end-to-end Cortex Agent pipeline** in less than a couple of hours.

***

## What You Will Build

- A working **Streamlit application** (`cortex_agents_v2.py`) that lets you create and manage Cortex Agents.
- Agents that combine structured analytics, unstructured search, and external APIs.
- A reusable **pattern** for building additional agents, Cortex Analysts, and Cortex Search integrations.
- An initial **foundation** for creating more complex "agents of agents".

***

## Repository Structure

```
Cortex-Agents-V2/
│
├── cortex_agents_v2.py         # Main Streamlit app for agent orchestration (focus here)
├── models/                     # Includes decorative classes & DB connection code
│   ├── sales_metric.yaml        # Sales metrics definition (to load into Snowflake stage)
│   └── ...
├── setup.sql                   # Creates all required Snowflake objects
├── requirements.txt            # Python/Streamlit package dependencies
└── README.md                   # Project documentation (this file)
```


***

## Step-by-Step Guide

### 1. Clone the Repository

```bash
git clone https://github.com/sarathi-aiml/Cortex-Agents-V2.git
cd Cortex-Agents-V2
```


### 2. Install Requirements

Make sure you have Python 3.9+ and Snowflake's Snowpark libraries available. Then install dependencies:

```bash
pip install -r requirements.txt
```


### 3. Configure Snowflake

Run the setup script to create necessary objects (stages, databases, roles, file formats, etc.) in your Snowflake account:

```sql
!source setup.sql
```


### 4. Load Sales Metrics File

Upload the `sales_metrics_model.yaml` file into the **models stage** in your Snowflake environment:

```sql
PUT file://models/sales_metrics_model.yaml @models;
```
Or use Snowsight UI to upload the file to the models stage

### 5. Run the Streamlit App

Launch the main Cortex Agent app:

```bash
streamlit run cortex_agents_v2.py
```

From here, you will use a simple UI to create and test your agents.

***

## Agent Components

### Cortex Analyst

Analyzes structured sales data with metrics defined in `sales_metrics_model.yaml`. Great for metrics, trends, and sales KPIs.

### Cortex Search

Searches across unstructured **sales conversation** data such as call transcripts, meeting notes, or chat logs.

### External API Integration

Demonstrates creating a UDF to connect to a stock price API. This shows how agents can connect to external services seamlessly.

### Email Tool

Includes a stored procedure for sending reports by email. This can be connected as a custom tool in your agents to automate report delivery.

***

## Extend Further

- Add more **Cortex Analysts** for other datasets.
- Build new **Cortex Search** indexes for additional unstructured sources.
- Use UDFs to integrate **other APIs** (financial, weather, healthcare, etc.).
- Create **agents of agents** by chaining together multiple reusable agent workflows.

![Cortex Agents Diagram](https://github.com/sarathi-aiml/Cortex-Agents-V2/blob/main/images/Agents-of-Agents.png?raw=true)

***

## Sample prompts

Create new thread and ask the following prompts: try switch thread and ask the followup prompts to see the context is maintained.

- List all the products we have? 

- which product have high deal value?

- which is at lowest?

- List all the sales people name and total sales ? 

- Among these who is top performer?

- what contributed to their sales? 

- who is at the bottom?

- What was the out come of last sales conversation and Technical deep dive with HealthTech Solutions Inc? Who is the sales rep assign to this company? what is the total deal value? how is this company HLTT doing in stock market recently?

***


## How to Create a Cortex Agent in Snowflake

1. **Login to Snowflake**
    - Go to: *AI & ML → Agents → Create Agent*
    ![Cortex Agents Diagram](https://github.com/sarathi-aiml/Cortex-Agents-V2/blob/main/images/CreateAgent.png?raw=true)

2. **Agent Setup**
    - After creating, click **Edit**.
    - **About**: Add name, description, and sample questions for user onboarding.
    - **Tools**: Add tools such as Cortex Analyst, Cortex Search, External API Function, and Email Procedure.
        - For each tool, provide usage instructions.
        - *Cortex Analyst*: Edit → set Warehouse to “Custom” and select the correct Snowflake warehouse.
    - **Orchestration**: Choose your model and set up orchestration logic:
        > Use Cortex Analyst for analysis, Cortex Search for documentation/context, general LLM for other queries; always prefer tabular and chart views, explain in detail, respond in English.
    - **Response Instruction**:
        > Provide detailed insights, cite sources, and explain analysis.
    - **Access**: Assign appropriate roles for agent access.



## Streamlit App Screenshots

![Cortex Agents Diagram](https://github.com/sarathi-aiml/Cortex-Agents-V2/blob/main/images/screen1.png?raw=true)
![Cortex Agents Diagram](https://github.com/sarathi-aiml/Cortex-Agents-V2/blob/main/images/screen2.png?raw=true)


***

**Enjoy building your end-to-end Cortex Agent workflow!**
