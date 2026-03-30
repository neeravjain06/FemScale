# Error Handling

## Standard Errors

- 422 Unprocessable Entity  
  - Triggered when `code` is empty or invalid  
  - Handled by FastAPI validation  

- 413 Request Too Large  
  - Triggered when `code` exceeds 50KB  
  - Request is rejected before queuing  

- 404 Not Found  
  - Returned when `job_id` does not exist  

## Execution Failures

- `failed`  
  - Non-zero exit code from function  
  - stderr is captured and returned  

- `timeout`  
  - Execution exceeds `timeout_sec`  
  - Container is killed  

## Retry Strategy

- No automatic retries in MVP  
- All failures are terminal  
- User must resubmit jobs manually  