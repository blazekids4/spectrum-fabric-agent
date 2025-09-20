import os
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import BingGroundingTool, MessageRole
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TelecomThreeAgentSystem:
    """Three-agent system for telecom competitive intelligence analysis"""
    
    def __init__(self):
        """Initialize the three-agent system"""
        # Get endpoints
        self.agent_endpoint = os.environ.get("PROJECT_ENDPOINT_MULTI_AGENT_CHARTER")
        self.reasoning_endpoint = os.environ.get("MODEL_ROUTER_ENDPOINT")
        
        if not self.agent_endpoint:
            raise ValueError("PROJECT_ENDPOINT_MULTI_AGENT_CHARTER environment variable required")
        if not self.reasoning_endpoint:
            raise ValueError("MODEL_ROUTER_ENDPOINT environment variable required")
        
        # Initialize clients
        credential = DefaultAzureCredential()
        self.agent_project_client = AIProjectClient(
            endpoint=self.agent_endpoint,
            credential=credential
        )
        self.reasoning_project_client = AIProjectClient(
            endpoint=self.reasoning_endpoint,
            credential=credential
        )
        
        # Agent IDs will be stored after creation
        self.table_reader_agent_id = None
        self.web_search_agent_id = None
        
    def get_or_create_table_reader_agent(self, agents_client: AgentsClient) -> str:
        """Create or get existing table reader agent for telecom data"""
        config_file = "telecom_table_reader_agent_config.json"
        
        # Try to load existing agent
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    agent_id = config.get('agent_id')
                    if agent_id:
                        try:
                            agent = agents_client.get_agent(agent_id)
                            print(f"Using existing table reader agent: {agent_id}")
                            return agent_id
                        except:
                            print("Existing table reader agent not found, creating new one...")
            except:
                pass
        
        # Create new agent
        print("Creating new telecom table reader agent...")
        
        model_deployment = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME", 
                                        os.environ.get("MODEL_DEPLOYMENT_NAME"))
        if not model_deployment:
            raise ValueError("AGENT_MODEL_DEPLOYMENT_NAME or MODEL_DEPLOYMENT_NAME required")
        
        instructions = """You are a telecom competitive intelligence specialist. When given table data:

1. Parse the structure precisely - identify columns for Week, Brand, Mentions, Promotions, Switches To/From
2. Calculate accurate numeric answers for queries (counts, sums, averages, differences)
3. Identify trends and patterns in mentions and switching behavior
4. Extract promotion names and their impact on switching
5. Present findings in structured format with exact numbers

IMPORTANT: 
- Be precise with ALL numeric calculations
- Quote exact promotion names from the data
- For week-over-week changes, show the calculation
- Always specify the time period for your analysis
- Distinguish between "Switches to Brand" (gains) and "Switches from Brand" (losses)"""
        
        agent = agents_client.create_agent(
            model=model_deployment,
            name="telecom-table-reader-agent",
            instructions=instructions
        )
        
        # Save config
        with open(config_file, 'w') as f:
            json.dump({'agent_id': agent.id}, f, indent=2)
        
        print(f"Created telecom table reader agent: {agent.id}")
        return agent.id
    
    def get_or_create_web_search_agent(self, agents_client: AgentsClient) -> str:
        """Create or get existing web search agent for telecom promotions"""
        config_file = "telecom_web_search_agent_config.json"
        
        # Try to load existing agent
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    agent_id = config.get('agent_id')
                    if agent_id:
                        try:
                            agent = agents_client.get_agent(agent_id)
                            print(f"Using existing web search agent: {agent_id}")
                            return agent_id
                        except:
                            print("Existing web search agent not found, creating new one...")
            except:
                pass
        
        # Create new agent with Bing tool
        print("Creating new telecom web search agent...")
        
        model_deployment = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME", 
                                        os.environ.get("MODEL_DEPLOYMENT_NAME"))
        if not model_deployment:
            raise ValueError("AGENT_MODEL_DEPLOYMENT_NAME or MODEL_DEPLOYMENT_NAME required")
        
        # Get Bing connection
        bing_connection_name = os.environ.get("BING_GROUNDED_CONNECTION_NAME")
        
        if bing_connection_name:
            try:
                connection = self.agent_project_client.connections.get(name=bing_connection_name)
                bing_tool = BingGroundingTool(connection_id=connection.id)
                print(f"Using Bing connection: {bing_connection_name}")
            except Exception as e:
                print(f"Could not resolve Bing connection: {e}")
                bing_tool = BingGroundingTool()
        else:
            bing_tool = BingGroundingTool()
        
        instructions = """You are a telecom promotion research specialist with Bing access. Your task:

1. Search for OFFICIAL carrier promotion details on their websites (prefer site:t-mobile.com, site:verizon.com, site:att.com)
2. Find press releases and news about telecom promotions and competitive moves
3. Look for promotion launch dates, terms, and customer eligibility
4. Search for industry analysis and customer sentiment about promotions
5. Return 2-5 HIGH-QUALITY results per query with:
   - Title
   - URL (complete, actual URL)
   - Published date
   - Brief snippet (key facts only)

IMPORTANT:
- Prioritize official carrier sites and reputable tech/telecom news sources
- Include publication dates to verify timing with data weeks
- Do NOT summarize beyond the snippet
- Always provide the COMPLETE URL for each result
- For promotions, focus on finding official terms and launch dates"""
        
        agent = agents_client.create_agent(
            model=model_deployment,
            name="telecom-web-search-agent", 
            instructions=instructions,
            tools=bing_tool.definitions
        )
        
        # Save config
        with open(config_file, 'w') as f:
            json.dump({'agent_id': agent.id}, f, indent=2)
        
        print(f"Created telecom web search agent: {agent.id}")
        return agent.id
    
    def needs_web_search(self, query: str) -> bool:
        """Determine if the query needs web search based on keywords"""
        numeric_keywords = ['number', 'count', 'total', 'sum', 'average', 'highest', 'lowest', 
                          'rank', 'how many', 'mentions', 'switches']
        causal_keywords = ['why', 'explain', 'cause', 'contribute', 'impact', 'effective', 
                          'priorities', 'tell us', 'reveal', 'momentum', 'opportunity']
        
        query_lower = query.lower()
        
        # Check if it's purely numeric
        is_numeric = any(keyword in query_lower for keyword in numeric_keywords)
        needs_context = any(keyword in query_lower for keyword in causal_keywords)
        
        # If it asks for sources or current info
        asks_for_sources = any(word in query_lower for word in ['source', 'cite', 'link'])
        
        return needs_context or asks_for_sources or 'promo' in query_lower
    
    def table_reader_task(self, agents_client: AgentsClient, table_data: str, query: str) -> str:
        """Execute table reading task with specific query"""
        print("\n=== Table Reader Agent ===")
        print(f"Query: {query}")
        
        # Create thread
        thread = agents_client.threads.create()
        
        # Construct targeted prompt
        prompt = f"""Here is the telecom competitor data:

{table_data}

Please answer this specific question:
{query}

Provide exact numeric answers where applicable. Show your calculations."""
        
        # Send message
        agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        
        # Run agent
        run = agents_client.runs.create(
            thread_id=thread.id, 
            agent_id=self.table_reader_agent_id
        )
        
        # Wait for completion
        timeout = 30
        elapsed = 0
        while run.status in ("queued", "in_progress") and elapsed < timeout:
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            elapsed += 1
        
        # Get response
        response = agents_client.messages.get_last_message_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT
        )
        
        if response and response.text_messages:
            result = "\n".join(t.text.value for t in response.text_messages)
            print(f"Table analysis complete.")
            return result
        
        return "No response from table reader agent"
    
    def web_search_task(self, agents_client: AgentsClient, context: str) -> str:
        """Execute web search task based on context"""
        print("\n=== Web Search Agent ===")
        
        # Create thread
        thread = agents_client.threads.create()
        
        # Send message
        agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=context
        )
        
        # Run agent
        run = agents_client.runs.create(
            thread_id=thread.id,
            agent_id=self.web_search_agent_id
        )
        
        # Wait for completion
        timeout = 60
        elapsed = 0
        while run.status in ("queued", "in_progress") and elapsed < timeout:
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            elapsed += 1
            
            if elapsed % 10 == 0:
                print(f"  Still searching... {elapsed}s elapsed")
        
        # Get response
        response = agents_client.messages.get_last_message_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT
        )
        
        if response and response.text_messages:
            result = "\n".join(t.text.value for t in response.text_messages)
            print(f"Web search complete.")
            return result
        
        return "No response from web search agent"
    
    def reasoning_analysis(self, question: str, table_result: str, web_results: str = None) -> str:
        """Use O3 reasoning model to provide final analysis"""
        print("\n=== O3 Reasoning Model Analysis ===")
        
        # Get model deployment
        model_deployment = os.environ.get("MODEL_ROUTER_DEPLOYMENT")
        if not model_deployment:
            raise ValueError("MODEL_ROUTER_DEPLOYMENT environment variable required")
        
        # Prepare prompt based on whether we have web results
        if web_results:
            prompt = f"""You are an expert telecom competitive analyst. Provide insight based on:

ORIGINAL QUESTION: {question}

NUMERIC ANALYSIS (from table data):
{table_result}

WEB SEARCH RESULTS (current market context):
{web_results}

Provide a business-focused answer that:
1. Uses the exact numbers from the table analysis
2. Explains causality and business implications 
3. Cites specific URLs from web results to support claims
4. Offers actionable insights for competitive strategy
5. Highlights risks and opportunities

Format with clear headline, 2-3 key points, and specific recommendations.
Every causal claim MUST have a URL citation."""
        else:
            # Numeric-only query
            prompt = f"""You are an expert telecom competitive analyst. 

QUESTION: {question}

NUMERIC ANALYSIS:
{table_result}

Provide a clear, concise answer that:
1. Highlights the key finding
2. Explains what this means for business strategy
3. Suggests follow-up analysis if relevant

Keep it brief and focused on the numbers provided."""

        # Use direct OpenAI client call
        openai_client = self.reasoning_project_client.get_openai_client(api_version="2024-12-01-preview")
        
        response = openai_client.chat.completions.create(
            model=model_deployment,
            messages=[
                {"role": "system", "content": "You are a telecom competitive intelligence expert. Base all numeric claims on the provided data. Cite web sources for context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        print(f"Reasoning analysis complete.")
        return result
    
    def process_paired_test(self, table_data: str, sql_prompt: str, narrative_prompt: str) -> Dict[str, Any]:
        """Process a paired test case (SQL baseline + narrative)"""
        print(f"\n{'='*60}")
        print(f"Processing paired test:")
        print(f"SQL: {sql_prompt}")
        print(f"Narrative: {narrative_prompt}")
        print("="*60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "sql_prompt": sql_prompt,
            "narrative_prompt": narrative_prompt,
        }
        
        with self.agent_project_client:
            with self.agent_project_client.agents as agents_client:
                # Initialize agents
                self.table_reader_agent_id = self.get_or_create_table_reader_agent(agents_client)
                self.web_search_agent_id = self.get_or_create_web_search_agent(agents_client)
                
                # Step 1: Get numeric answer from table
                table_result = self.table_reader_task(agents_client, table_data, sql_prompt)
                results["sql_answer"] = table_result
                
                # Step 2: Determine if narrative needs web search
                if self.needs_web_search(narrative_prompt):
                    # Extract context for web search
                    search_context = self.create_search_context(narrative_prompt, table_result)
                    web_results = self.web_search_task(agents_client, search_context)
                    results["web_search_results"] = web_results
                else:
                    web_results = None
                    results["web_search_results"] = "Not needed - numeric only"
                
                # Step 3: Generate narrative with reasoning model
                narrative_result = self.reasoning_analysis(
                    narrative_prompt, 
                    table_result, 
                    web_results
                )
                results["narrative_answer"] = narrative_result
        
        return results
    
    def create_search_context(self, narrative_prompt: str, table_result: str) -> str:
        """Create search context from narrative prompt and table results"""
        # Extract key entities and promotions from the prompts
        context_parts = []
        
        # Look for specific weeks mentioned
        import re
        week_pattern = r'(W\d{2}|week \d{4}-W\d{2})'
        weeks = re.findall(week_pattern, narrative_prompt + " " + table_result)
        
        # Look for brand names
        brands = []
        for brand in ['T-Mobile', 'Verizon', 'AT&T', 'Dish Wireless', 'US Cellular']:
            if brand.lower() in (narrative_prompt + " " + table_result).lower():
                brands.append(brand)
        
        # Look for promotion keywords in table result
        promo_keywords = []
        if 'unlimited' in table_result.lower():
            promo_keywords.append('unlimited plan')
        if 'iphone' in table_result.lower():
            promo_keywords.append('iPhone promotion')
        if 'switch' in table_result.lower():
            promo_keywords.append('switch offer')
        if 'nfl' in table_result.lower():
            promo_keywords.append('NFL Sunday Ticket')
        if 'back-to-school' in table_result.lower():
            promo_keywords.append('back to school promotion')
            
        # Build search query
        search_parts = []
        
        if brands:
            for brand in brands[:2]:  # Limit to top 2 brands
                brand_query = f'"{brand}" '
                if promo_keywords:
                    brand_query += " ".join(promo_keywords[:2])
                brand_query += " 2025 site:" + brand.lower().replace(' ', '').replace('&', '') + ".com"
                search_parts.append(brand_query)
        
        # Add news search
        if brands and (weeks or promo_keywords):
            news_query = f'"{brands[0]}" '
            if promo_keywords:
                news_query += f'"{promo_keywords[0]}" '
            news_query += "announcement 2025 site:fiercewireless.com OR site:lightreading.com"
            search_parts.append(news_query)
        
        search_context = f"""Search for information about:
{chr(10).join(f"- {part}" for part in search_parts)}

Focus on:
1. Official promotion details and launch dates
2. Terms and conditions 
3. Industry analysis of competitive impact
4. Customer response data if available

Return 3-5 most relevant results with complete URLs."""
        
        return search_context
    
    def load_telecom_data(self) -> str:
        """Load the telecom dataset from markdown file"""
        # Try different possible paths
        possible_paths = [
            os.path.join('.charter_project', 'data', 'comp_mentions_and_promotions_dataset_long.md'),
            os.path.join('data', 'comp_mentions_and_promotions_dataset_long.md'),
            'comp_mentions_and_promotions_dataset_long.md',
            os.path.join(os.path.dirname(__file__), 'data', 'comp_mentions_and_promotions_dataset_long.md')
        ]
        
        md_content = None
        used_path = None
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Loading data from: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                used_path = path
                break
        
        if not md_content:
            raise FileNotFoundError(f"Could not find data file. Tried paths: {possible_paths}")
        
        # Extract the table from markdown
        # The table starts after the header line and continues until a blank line or end
        lines = md_content.split('\n')
        
        # Find the table
        table_started = False
        table_lines = []
        
        for line in lines:
            if '| Week' in line and '| Brand' in line:  # Header line
                table_started = True
                continue
            elif table_started and line.startswith('|---'):  # Separator line
                continue
            elif table_started and line.strip().startswith('|'):  # Data line
                table_lines.append(line.strip())
            elif table_started and not line.strip():  # Empty line, table ended
                break
        
        # Convert markdown table to CSV format
        csv_lines = []
        
        # Add header
        csv_lines.append('Week,Brand,Mentions,Promotions Driving Switching,Switches to Brand,Switches from Brand')
        
        # Process data lines
        for line in table_lines:
            # Remove leading/trailing pipes and split
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 6:  # Ensure we have all columns
                csv_lines.append(','.join(parts))
        
        csv_data = '\n'.join(csv_lines)
        
        print(f"Loaded {len(table_lines)} rows of data")
        
        return csv_data


def run_paired_tests():
    """Run all 10 paired test cases"""
    system = TelecomThreeAgentSystem()
    
    try:
        table_data = system.load_telecom_data()
    except FileNotFoundError as e:
        print(f"Error loading data: {e}")
        print("Please ensure the data file exists at: .charter_project/data/comp_mentions_and_promotions_dataset_long.md")
        return
    
    # Define the 10 paired test cases
    test_cases = [
        {
            "name": "Test 1: Weekly Lookup",
            "sql": "What was the number of T-Mobile mentions in week 2025-W34?",
            "narrative": "How might the promotions listed for T-Mobile in week 2025-W34 have contributed to its mention volume?"
        },
        {
            "name": "Test 2: Total Mentions", 
            "sql": "What is the total number of mentions for Verizon across all 12 weeks?",
            "narrative": "What does this total tell us about Verizon's competitive standing compared to T-Mobile and AT&T?"
        },
        {
            "name": "Test 3: Comparisons",
            "sql": "In week 2025-W30, how many more mentions did T-Mobile have compared to AT&T?",
            "narrative": "What could explain the difference in mentions between T-Mobile and AT&T during week 2025-W30?"
        },
        {
            "name": "Test 4: Aggregations",
            "sql": "Which brand had the highest average mentions per week across the dataset?",
            "narrative": "Summarize what this reveals about long-term customer attention trends in the industry."
        },
        {
            "name": "Test 5: Switching Behavior",
            "sql": "Which brand gained the most switches-to-brand in week 2025-W32?",
            "narrative": "Based on the promotion driving those switches, explain why customers may have chosen that brand."
        },
        {
            "name": "Test 6: Trend Detection",
            "sql": "Show the week-over-week change in mentions for T-Mobile between W28 and W32.",
            "narrative": "Describe whether this indicates momentum building for T-Mobile and what risks could stall that momentum."
        },
        {
            "name": "Test 7: Top-N",
            "sql": "Rank all brands by their total mentions from highest to lowest.",
            "narrative": "Narratively explain what this ranking suggests about the competitive landscape."
        },
        {
            "name": "Test 8: Hypothetical Forecasting",
            "sql": "What was the average increase in T-Mobile mentions per week between W30 and W37?",
            "narrative": "If that increase continues, how many mentions would T-Mobile have by W40, and what business opportunities could this create?"
        },
        {
            "name": "Test 9: Promo Impact",
            "sql": "List all T-Mobile promotions that led to more than 300 switches in a given week.",
            "narrative": "Which of these promotions appears most effective, and what does that tell us about customer priorities?"
        },
        {
            "name": "Test 10: Executive Summary",
            "sql": "What are the total switches-to-brand and switches-from-brand for each competitor across all 12 weeks?",
            "narrative": "Using those totals, write a concise executive summary highlighting winners, losers, and potential threats in the marketplace."
        }
    ]
    
    # Process tests
    all_results = []
    
    # You can run a subset for testing
    test_subset = test_cases[:3]  # Run first 3 tests for demo
    
    for i, test in enumerate(test_subset, 1):
        print(f"\n\n{'#'*60}")
        print(f"Running {test['name']}")
        print(f"{'#'*60}")
        
        try:
            result = system.process_paired_test(
                table_data,
                test["sql"],
                test["narrative"]
            )
            result["test_name"] = test["name"]
            all_results.append(result)
            
            # Print summary
            print(f"\n=== SQL Answer ===")
            print(result["sql_answer"][:200] + "..." if len(result["sql_answer"]) > 200 else result["sql_answer"])
            
            print(f"\n=== Narrative Answer ===")
            print(result["narrative_answer"][:300] + "..." if len(result["narrative_answer"]) > 300 else result["narrative_answer"])
            
        except Exception as e:
            print(f"Error in test {i}: {str(e)}")
            all_results.append({
                "test_name": test["name"],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    # Save all results
    output_file = f"telecom_paired_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\nAll test results saved to: {output_file}")
    
    # Generate summary report
    generate_test_summary(all_results)


def generate_test_summary(results: List[Dict]):
    """Generate a summary report of test results"""
    print("\n" + "="*60)
    print("TEST SUMMARY REPORT")
    print("="*60)
    
    for result in results:
        print(f"\n{result['test_name']}")
        if 'error' in result:
            print(f"  Status: FAILED - {result['error']}")
        else:
            print(f"  Status: SUCCESS")
            print(f"  SQL Answer Length: {len(result['sql_answer'].split())} words")
            print(f"  Narrative Answer Length: {len(result['narrative_answer'].split())} words")
            print(f"  Web Search: {'Yes' if result['web_search_results'] != 'Not needed - numeric only' else 'No'}")


def main():
    """Main entry point - can run single query or full test suite"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run the full test suite
        run_paired_tests()
    else:
        # Run a single example
        system = TelecomThreeAgentSystem()
        
        try:
            table_data = system.load_telecom_data()
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            print("Please ensure the data file exists at: .charter_project/data/comp_mentions_and_promotions_dataset_long.md")
            return
        
        # Example single query
        result = system.process_paired_test(
            table_data,
            "What was the number of T-Mobile mentions in week 2025-W34?",
            "How might the promotions listed for T-Mobile in week 2025-W34 have contributed to its mention volume?"
        )
        
        # Save result
        output_file = f"telecom_single_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nResult saved to: {output_file}")
        
        # Print formatted output
        print("\n" + "="*60)
        print("FINAL RESULT")
        print("="*60)
        print(f"\nSQL Answer:\n{result['sql_answer']}")
        print(f"\nNarrative Answer:\n{result['narrative_answer']}")


if __name__ == "__main__":
    main()