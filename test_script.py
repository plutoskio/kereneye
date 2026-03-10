import asyncio
from data.collector import DataCollector
from crew.research_crew import run_news_analysis_crew

async def test_news():
    collector = DataCollector()
    print("Collecting data...")
    data = collector.collect('AAPL')
    
    print("\nRecent News found:", len(data.recent_news))
    if data.recent_news:
        print("Sample:", data.recent_news[0])
        
    print("\nRunning crew...")
    def cb(msg):
        print("Status:", msg)
    
    result = run_news_analysis_crew(data, cb)
    print("\nResult:\n", result)

if __name__ == "__main__":
    asyncio.run(test_news())
