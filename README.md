# data260-0932

## Homework 1 Report Answers
1. The prior context is resent every term because the model doesn’t have memory between the API calls made. Therefore, you need the client to send the previous conversation every time in order for the model to remember and go off on that.
2. A system prompt is where to set rules and the roles for the models in the conversation. This affects how the interactions are done and affects everything. This is unchanged. A user message is a user input that affects it for one term and this is changed within the model as it summarizes it to be something else. This doesn't continue to carry importance later unlike the system prompt. 
3. Input tokens grow because each request causes a resending of the entire history for memory. It continues to add up as the conversation gets longer as it appends the history to the new message.
4. The limits of growth are the model’s max token limit. Because the input tokens add up quickly, the model can fail if the max token is reached when getting the resent memory. Tokens are also expensive and limited. It is difficult to add to the model’s max token limit because this is another added cost.

## Homework 3 Report Answers
1. Find at least one confidently scored retrieval that does not contain the answer. If your five questions don't produce one, add questions until you find one. Explain why the embedding likely considered it similar.

For the query “Which package has the most vulnerabilities in the dataset?”, I noticed that the first rank labeled the package numpy as the answer. This is incorrect and the cosine similarity is 0.429 approximately. It shows that there is one vulnerability for NumPy, while the Pillow package has 52 vulnerabilities. The Pillow package answer is ranked below the NumPy one which shows that the most confident score retrieval does not contain the correct answer. Its most likely considered similar because the keywords in the query hit the package.txt file. The embedding only accounts for the wording similarity, so the vulnerability count value is not used for the comparison. Therefore, NumPy was ranked first.

2. Observations (1–2 short paragraphs):
Discuss why one technique performed better on this query (e.g., sentence coherence, semantic boundary detection, token-budget alignment, context carried via sentence window).

The results of the pipeline show that the sentence window retrieval did the best when answering the query "What bug affected Paramiko's write_private_key_file?". Because the query is simple, I believe the cosine similarity for sentence window technique was ranked first with a value of 0.7712. Token and semantic respectively had 0.7290 and 0.7150. It appears the sentence window result showed 315 characters, which is considerably less compared to the other techniques. I believe with less characters it was able to find the answer faster with less of a chance of it getting unnecessary information. 

If the best technique differs across your optional extra queries, mention it.

The best technique is the sentence window technique. By looking at all the results, I see that the top two cosine similarities are 0.7712 and 0.7256 for the sentence window technique. These cosine similarities are for the queries asking about Paramiko and PyYAML packages specifically. The query about NumPy and which packages have the most vulnerabilities show that the token technique is the best. These cosine similarities are the third and fourth highest. The values are 0.6878 and 0.4287. There is a noticeable gap between the top 2 and the third and fourth highest. Lastly, the last question about the RCE has a fifth highest cosine similarity value of 0.4515. The best technique for this question is the sentence window method. 

3. Your conclusion (2–5 sentences):
State which technique you judge best for this corpus and why supported by your measurements.

For this whole experiment, I think the sentence window technique is the best because it showed the strongest cosine similarity out of all three techniques. Out of the five questions, sentence window technique had the highest cosine similarity of all three techniques for 3 out of 5 questions. Additionally, the top two cosine similarity values are from the sentence window technique. The values are 0.7712 and 0.7256 for the query questions about Paramiko and PyYAML packages specifically. I believed this technique is also the best because of the smaller 

