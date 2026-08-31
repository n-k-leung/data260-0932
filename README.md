# data260-0932

## Homework 1 Report Answers
1. The prior context is resent every term because the model doesn’t have memory between the API calls made. Therefore, you need the client to send the previous conversation every time in order for the model to remember and go off on that.
2. A system prompt is where to set rules and the roles for the models in the conversation. This affects how the interactions are done and affects everything. This is unchanged. A user message is a user input that affects it for one term and this is changed within the model as it summarizes it to be something else. This doesn't continue to carry importance later unlike the system prompt. 
3. Input tokens grow because each request causes a resending of the entire history for memory. It continues to add up as the conversation gets longer as it appends the history to the new message.
4. The limits of growth are the model’s max token limit. Because the input tokens add up quickly, the model can fail if the max token is reached when getting the resent memory. Tokens are also expensive and limited. It is difficult to add to the model’s max token limit because this is another added cost.


