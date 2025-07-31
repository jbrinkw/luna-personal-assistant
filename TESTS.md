# Luna Personal Assistant - Comprehensive Test Suite

This document provides a complete overview of the test suite for the Luna Personal Assistant MCP servers. The test suite uses OpenAI Agents SDK with GPT-4.1 to provide comprehensive automated testing with LLM-based evaluation.

## 🎯 Overview

The Luna Personal Assistant consists of three specialized MCP servers:

- **ChefByte**: Kitchen and meal management system (SQLite database)
- **CoachByte**: Workout tracking system (PostgreSQL database)  
- **GeneralByte**: Home Assistant integration for notifications and todo management

Each server has its own comprehensive test agent that evaluates all functionality using natural language prompts and automated LLM judging.

## 🏗️ Test Architecture

### Core Components

1. **Individual Test Agents**: Specialized test suites for each MCP server
2. **Master Test Script**: Orchestrates all tests and generates unified reports
3. **LLM Judging**: Automated evaluation using GPT-4.1 to assess functionality
4. **Database Reset**: Ensures consistent test environment with sample data

### Test Philosophy

- **Natural Language Testing**: Uses human-like prompts to test tools as users would
- **CRUD Verification**: Tests database operations with before/after state comparison
- **Automated Evaluation**: LLM judges assess test results for accuracy and completeness
- **Comprehensive Coverage**: Tests all available tools, edge cases, and error conditions

## 🧪 Test Suites

### ChefByte Test Suite (`chefbyte/test_agent.py`)

Tests the kitchen and meal management system with SQLite database.

#### Test Categories

1. **CRUD Tests**
   - Inventory management (add/remove ingredients)
   - Taste profile updates 
   - Saved meals management
   - Shopping list operations
   - Daily meal planning

2. **Action Tools**
   - Meal planning workflow
   - Meal suggestion generation
   - New meal ideation

3. **Pull Tools** 
   - Inventory retrieval
   - Taste profile queries
   - Saved meals listing
   - Shopping list viewing
   - Daily plan checking
   - In-stock meal availability
   - Meal ideas browsing

4. **Push Tools**
   - Complex inventory updates
   - Taste profile refinements
   - Meal modifications
   - Shopping list management
   - Daily notes updates

#### Sample Test Prompts

```
"Add 2 pounds of ground turkey to the inventory with expiration date next week"
"Update my taste profile to include that I love Mediterranean food"
"Help me plan meals for the next 3 days using ingredients I have in my inventory"
"I used 1 pound of ground beef and 2 cups of pasta for dinner tonight. Update my inventory."
```

#### Database Reset

Before each test run, the SQLite database is reset to a known state with:
- Sample inventory items (39 ingredients)
- Comprehensive taste profile
- 23 saved meals with ingredients and recipes
- 9 meal ideas with detailed instructions
- Default shopping list items

### CoachByte Test Suite (`coachbyte/test_agent.py`)

Tests the workout tracking system with PostgreSQL database.

#### Test Categories

1. **CRUD Tests**
   - Daily workout planning
   - Set completion tracking
   - Workout logging
   - Weekly split configuration
   - Workout summary updates

2. **Workout Tools**
   - Plan creation
   - Set execution with modifications
   - Progress tracking
   - Split management

3. **Query Tools**
   - Today's plan viewing
   - Recent history analysis
   - Weekly split display
   - Exercise analysis
   - SQL query execution

4. **Timer Tools**
   - Rest timer setting
   - Timer status checking
   - Workout duration tracking

5. **Advanced Tools**
   - Complex periodized planning
   - Workout modifications
   - Progress comparisons
   - Database operations

#### Sample Test Prompts

```
"Create a new daily workout plan with 3 sets of bench press at 155 lbs for 8 reps"
"I just completed my first planned set. Mark it as done with the planned weight and reps"
"Show me my progress on bench press over the last week"
"Set a 3-minute rest timer for my next set"
```

#### Database Reset

Before each test run, the PostgreSQL database is reset with:
- 3 days of MMA-focused workout data
- 14 exercise types (push-ups, pull-ups, bench press, etc.)  
- Dynamic dates (today, yesterday, day before)
- Comprehensive planned and completed sets
- Workout summaries and progress tracking

### GeneralByte Test Suite (`generalbyte/test_agent.py`)

Tests the Home Assistant integration for notifications and todo management.

#### Test Categories

1. **Notification Tests**
   - Basic notification sending
   - Custom messages and titles
   - Urgent notifications
   - Status notifications

2. **Todo List Tests**
   - Todo list retrieval
   - Status filtering
   - Item searching
   - Summary generation

3. **Todo CRUD Tests**
   - Item creation
   - Status updates
   - Content modification  
   - Item deletion

4. **Integration Tests**
   - Combined operations
   - Multi-step workflows
   - Productivity tracking
   - Daily planning

5. **Error Handling Tests**
   - Invalid operations
   - Missing items
   - Special characters
   - Service failures

6. **Connectivity Tests**
   - Home Assistant connection
   - Service accessibility
   - Configuration validation

#### Sample Test Prompts

```
"Send a test notification with the message 'GeneralByte test suite is running'"
"Create a new todo item: 'Test GeneralByte MCP integration'"
"Show me my complete todo list with all items and their status"
"Create a todo item and then send me a notification to remind me about it"
```

#### No Database Reset

GeneralByte integrates with Home Assistant services and doesn't maintain its own database. Tests focus on functional integration and service connectivity.

## 🚀 Running Tests

### Prerequisites

1. **OpenAI API Key**: Set in environment for LLM judging
2. **Python Dependencies**: Install required packages
3. **Database Access**: 
   - ChefByte: SQLite (local file)
   - CoachByte: PostgreSQL (configured connection)
   - GeneralByte: Home Assistant API access

### Individual Test Execution

Run specific test suites independently:

```bash
# ChefByte tests
python chefbyte/test_agent.py

# CoachByte tests  
python coachbyte/test_agent.py

# GeneralByte tests
python generalbyte/test_agent.py
```

### Master Test Suite

Run all tests with unified reporting:

```bash
python run_all_tests.py
```

The master script provides:
- Parallel or sequential execution
- Timeout management
- Comprehensive reporting
- Error handling and recovery

## 📊 Test Results

### Generated Files

Each test run produces multiple output files:

#### Individual Agent Results
- `chefbyte_test_results.json` - Detailed ChefByte test data
- `chefbyte_test_evaluation.txt` - LLM evaluation of ChefByte tests
- `coachbyte_test_results.json` - Detailed CoachByte test data  
- `coachbyte_test_evaluation.txt` - LLM evaluation of CoachByte tests
- `generalbyte_test_results.json` - Detailed GeneralByte test data
- `generalbyte_test_evaluation.txt` - LLM evaluation of GeneralByte tests

#### Master Test Results
- `master_test_results.json` - Complete test suite results
- `master_test_summary.txt` - Human-readable summary report

### Result Structure

Test results include:
- Test execution metadata (timing, model used)
- Before/after database states for CRUD tests
- Agent responses to natural language prompts
- LLM evaluation and scoring
- Error details and debugging information

### LLM Evaluation Criteria

The LLM judge evaluates tests based on:

1. **Functionality**: Did the tools work as expected?
2. **Data Integrity**: Were database changes applied correctly?
3. **Response Quality**: Are agent responses helpful and accurate?
4. **Error Handling**: How well are failures managed?
5. **Coverage**: Are all tool capabilities tested?

Each category receives a PASS/FAIL rating with detailed reasoning.

## 🔧 Test Configuration

### Timeouts

- ChefByte: 10 minutes (complex meal planning operations)
- CoachByte: 10 minutes (database operations and history analysis)
- GeneralByte: 5 minutes (simple service calls)

### Models Used

- Primary Agent: GPT-4.1 (configured as "gpt-4o")
- LLM Judge: GPT-4.1 for consistent evaluation
- Temperature: 0.1 for deterministic judging

### Server Ports

- ChefByte MCP Server: 8000
- CoachByte MCP Server: 8100  
- GeneralByte MCP Server: 8050

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Failures**
   - Verify database services are running
   - Check connection credentials
   - Ensure sample data loading works

2. **MCP Server Startup Issues**
   - Check port availability
   - Verify Python dependencies
   - Review server logs for errors

3. **OpenAI API Issues**
   - Confirm API key is set correctly
   - Check API rate limits and quotas
   - Verify model access permissions

4. **Home Assistant Connection (GeneralByte)**
   - Validate HA_URL and HA_TOKEN environment variables
   - Test Home Assistant API accessibility
   - Check notification service configuration

### Debug Mode

Enable verbose logging in individual test agents:
- Add `verbose=True` to database connections
- Set higher timeout values for debugging
- Use `print()` statements for intermediate results

### Selective Testing

Run specific test categories within an agent:
- Modify the test agent to run only desired functions
- Comment out sections in `run_all_tests()` methods
- Use breakpoints for step-by-step execution

## 📈 Test Maintenance

### Adding New Tests

1. **For new tools**: Add test prompts to appropriate test categories
2. **For new databases**: Create snapshot functions and CRUD tests
3. **For new integrations**: Add connectivity and functional tests

### Updating Sample Data

1. **ChefByte**: Modify `chefbyte/debug/reset_db.py`
2. **CoachByte**: Update `coachbyte/load_sample_data.py`
3. **GeneralByte**: Configure Home Assistant test entities

### Improving LLM Evaluation

1. Refine evaluation prompts in `create_llm_judge_prompt()`
2. Add specific criteria for new functionality
3. Adjust evaluation categories and scoring

## 🎖️ Best Practices

### Writing Test Prompts

- Use natural, conversational language
- Be specific about expected outcomes
- Include realistic user scenarios
- Test both success and failure cases

### Database Testing

- Always capture before/after states
- Test edge cases and constraints
- Verify referential integrity
- Check for data consistency

### Error Testing  

- Test invalid inputs
- Verify graceful failure handling
- Check error message quality
- Ensure system stability

### Performance Considerations

- Monitor test execution times
- Use appropriate timeouts
- Consider parallel execution limits
- Optimize database operations

## 📋 Test Coverage Matrix

| Component | CRUD | Actions | Queries | Errors | Integration |
|-----------|------|---------|---------|---------|-------------|
| ChefByte Inventory | ✅ | ✅ | ✅ | ✅ | ✅ |
| ChefByte Meals | ✅ | ✅ | ✅ | ✅ | ✅ |
| ChefByte Planning | ✅ | ✅ | ✅ | ✅ | ✅ |
| CoachByte Workouts | ✅ | ✅ | ✅ | ✅ | ✅ |
| CoachByte Splits | ✅ | ✅ | ✅ | ✅ | ✅ |
| CoachByte Timers | N/A | ✅ | ✅ | ✅ | ✅ |
| GeneralByte Notifications | N/A | ✅ | N/A | ✅ | ✅ |
| GeneralByte Todos | ✅ | ✅ | ✅ | ✅ | ✅ |

## 🚀 Future Enhancements

- **Performance Testing**: Add load testing for concurrent users
- **Integration Testing**: Cross-system functionality testing
- **Regression Testing**: Automated comparison with previous runs
- **Visual Reports**: HTML dashboards for test results
- **CI/CD Integration**: Automated testing in deployment pipeline
- **Mock Testing**: Offline testing with simulated services

---

This comprehensive test suite ensures the Luna Personal Assistant MCP servers are reliable, functional, and ready for production use. The combination of natural language testing and LLM evaluation provides thorough coverage while maintaining readability and maintainability.