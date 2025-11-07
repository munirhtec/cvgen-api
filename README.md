<img width="713" height="547" alt="image" src="https://github.com/user-attachments/assets/87418a7a-c16d-41fb-a918-02b32d9613bf" />

# CV Generation and Review System

This system automates the creation, review, and refinement of CVs using employee data. The workflow uses multiple agents to generate drafts, evaluate their quality, and refine them based on feedback.

## Key Components

### 1. **Drafting Agent**  
Generates an initial CV draft based on employee data. It maps various fields (e.g., `personalInformation`, `professionalSkills`) to a predefined schema.

### 2. **Review Agent**  
Reviews the generated CV draft against a checklist, returning feedback on completeness and quality.

### 3. **Refinement Agent**  
Refines the CV draft based on review feedback, improving clarity and professionalism.

### 4. **CVPipeline**  
A pipeline that manages the entire CV creation, review, and refinement process for an employee. It tracks the draft, feedback history, and allows modifications.

### 5. **FAISS-Based Search**  
Finds employees based on fuzzy matching, utilizing vectors for similarity scoring (using `SentenceTransformer`).

## Classes & Functions

### `DraftingAgent`
- **`generate(employee_record)`**: Generates a CV draft based on employee data.

### `ReviewAgent`
- **`review(draft)`**: Reviews the CV draft and returns feedback.

### `RefinementAgent`
- **`refine(draft, employee_record)`**: Refines the CV draft based on feedback.

### `CVPipeline`
Handles the CV process for an employee.
- **`draft()`**: Creates an initial CV draft.
- **`review()`**: Reviews the draft.
- **`refine()`**: Refines the draft based on feedback.
- **`add_feedback(feedback_item)`**: Adds feedback to the draft.

### Search Functions
- **`find_employee(query)`**: Finds an employee by ID, name, email, or phone.
- **`search_similar(query)`**: Finds similar records using FAISS-based vector search.

## API Endpoints (FastAPI)

- **POST `/start/{employee_query}`**: Start a new CV draft for an employee based on a query (ID, name, etc.).
- **GET `/draft/{employee_id}`**: Retrieve the current CV draft.
- **POST `/review/{employee_id}`**: Review the CV draft.
- **POST `/refine/{employee_id}`**: Refine the CV draft based on feedback.
- **POST `/feedback`**: Submit feedback for refinement.
- **POST `/reset/{employee_id}`**: Reset the CV pipeline.
