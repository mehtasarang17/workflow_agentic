# Test Prompts for Workflow Application

## Available Integrations
- **Webhook**: Trigger
- **Email**: ID 48
- **GitHub**: ID 50
- **Gitlab**: ID 53
- **AWS**: ID 5
- **Azure**: ID 55
- **GCP**: ID 54
- **Conditions**: Logic nodes
- **Logs**: Audit/Debugging

---

## 🟢 Light Workflows (Simple: 1-10)

### 1. **Email - Quick Alert**
```
Create a workflow that receives a webhook, then sends an email to mehtasarang17@gmail.com with subject "Light Alert" and body "Simple test notification".
```

### 2. **Gitlab - Issue Creation**
```
Build a workflow that receives a webhook, then creates a new issue in Gitlab project "mehtasarang17/test-repo" with title "New Task" using integration ID 53.
```

### 3. **Github - Issue Creation**
```
Create a workflow that receives a webhook, then creates a new issue in Github repository "mehtasarang17/test-repo" with title "Documentation Update" using integration ID 50.
```

### 4. **AWS - Dynamic WAF Check**
```
Create a workflow that receives a webhook containing an "ipset_name", then lists blocked IPs in that AWS WAF IP set using integration ID 5, and logs the result.
```

### 5. **Hybrid - Email & Log**
```
Build a workflow that receives a webhook, sends a notification email to mehtasarang17@gmail.com, and then logs "Notification Sent" to the system.
```

### 6. **Azure - Networking Status**
```
Create a workflow that checks if Azure accelerated networking is disabled using integration ID 55, and logs the result.
```

### 7. **GCP - Bucket Security Check**
```
Create a workflow that checks for public bucket policy access in GCP and sends an email report to mehtasarang17@gmail.com and also creates a gitlab issue.
```

### 8. **GitLab - Task Log**
```
Build a workflow that creates a Gitlab issue (ID 53) and then immediately logs a message saying "Gitlab issue tracked".
```

### 9. **Email - Admin Notification**
```
Create a workflow to send an email to mehtasarang17@gmail.com with subject "Admin Alert" and a body explaining that a new event was triggered.
```

### 10. **Logs - Traceability**
```
Build a workflow that receives a webhook and logs two separate messages: "Event Received" and then "Processing Started".
```

---

## 🟡 Medium Workflows (Moderate: 11-20)

### 11. **Conditional Email Alert**
```
Create a workflow that receives a webhook containing a "status" field. Use a condition to check if status is "critical". If true, send an email to mehtasarang17@gmail.com. If false, log the status as "normal".
```

### 12. **AWS - Dynamic IP Blocking**
```
Build a workflow that receives a webhook with "ip_to_block" and "target_ipset". Use AWS (ID 5) to block that IP in the specified IP set, then send a confirmation email to mehtasarang17@gmail.com.
```

### 13. **Azure - Admin Privilege Check**
```
Create a workflow that checks for Azure full admin privileges. If found, create a Github issue (ID 50) and log the security finding else send email to mehtasarang17@gmail.com.
```

### 14. **GCP - Insecure Hosting Alert**
```
Build a workflow that checks for insecure website hosting in GCP (ID 54). If found, send an email to mehtasarang17@gmail.com and create a Gitlab issue (ID 53).
```

### 15. **Github - Action & Notify**
```
Build a workflow that creates a Github issue in "mehtasarang17/test-repo" (ID 50), then sends a follow-up email to mehtasarang17@gmail.com with the issue details, and logs the completion.
```

### 16. **Webhook to Condition to Cloud Check**
```
Create a workflow where a webhook triggers a check. If the webhook payload "cloud" equals "aws", perform an S3 public access check (ID 5). Otherwise, log "Skipping cloud check".
```

### 17. **GitHub Listing → Email Summary**
```
Build a workflow that lists all Github repositories (ID 50) and then sends an email to mehtasarang17@gmail.com containing the repository list.
```

### 18. **Azure Networking Alert**
```
Build a workflow that checks Azure accelerated networking (ID 55) and if disabled, sends a critical email to mehtasarang17@gmail.com.
```

### 19. **Dual Notification (Email + Log)**
```
Create a workflow that receives a webhook, sends a summary email to mehtasarang17@gmail.com, and logs the entire payload from the webhook for debugging.
```

### 20. **GCP Governance Check**
```
Build a workflow that checks GCP bucket policy public access (ID 54). If public access is detected, create a Github issue (ID 50) titled "Fix GCP Bucket Permissions".
```

---

## 🔴 Heavy Workflows (Complex: 21-30)

### 21. **Multi-Source Incident Sync**
```
Build a complex workflow:
1. Receive a webhook regarding a security bug.
2. Create an issue in Github repository "mehtasarang17/test-repo" (ID 50).
3. Create a mirror issue in Gitlab project "mehtasarang17/test-repo" (ID 53).
4. Send a consolidated email to mehtasarang17@gmail.com with links/IDs from both platforms.
5. Log a "Double-Sync Completed" message.
```

### 22. **Multi-Cloud Security Audit (Comprehensive)**
```
Create a workflow that:
1. Checks for IAM full admin privileges in AWS (ID 5).
2. Checks Azure admin privileges (ID 55).
3. Checks GCP bucket policy public access (ID 54).
4. Sends a combined email report to mehtasarang17@gmail.com summarizing the findings.
```

### 23. **Gitlab Project Check & Sync**
```
Build a workflow that:
1. Receives a webhook.
2. Lists Gitlab projects (ID 53).
3. Uses a condition to check if "mehtasarang17/test-repo" exists in the list.
4. If it exists: Create an issue in that project.
5. If not: Send an email to mehtasarang17@gmail.com saying "Project not found".
6. Log the outcome of the search.
```

### 24. **Github Repo Check & Sync**
```
Build a workflow that:
1. Receives a webhook.
2. Lists Github repositories (ID 50).
3. Uses a condition to check if "mehtasarang17/test-repo" exists.
4. If it exists: Create a Github issue.
5. If not: Log "Sync failed - repository missing".
6. Send a final status email to mehtasarang17@gmail.com.
```

### 25. **The Ultimate Cloud Triage**
```
Design a comprehensive triage workflow:
1. Receive a webhook containing "provider" (aws/azure/gcp).
2. If "aws": Check IAM admin privileges (ID 5) -> Send Email -> Log result.
3. If "azure": Check networking (ID 55) -> Send Email -> Log result.
4. If "gcp": Check bucket policy (ID 54) -> Send Email -> Log result.
5. Finally, create a summary Github issue (ID 50) with the triage status.
```

### 26. **Cloud to Issue Mirroring**
```
Build a workflow that checks Azure admin privileges (ID 55), then takes the result and creates both a Github issue (ID 50) and a Gitlab issue (ID 53) for remediation tracking, and finally logs "Remediation issues created".
```

### 27. **Sequential Multi-Check Logic**
```
Create a workflow:
1. Webhook trigger.
2. Condition 1: Check if "audit" is true.
3. If true, run AWS (5) and GCP (54) security tasks.
4. If false, check Condition 2: is "emergency" true?
5. If true, send a "Critical Response" email to mehtasarang17@gmail.com.
6. Regardless of outcome, log the final logic path taken.
```

### 28. **Inventory Sync & Alert**
```
Build a workflow that:
1. Lists Github repos (ID 50).
2. Lists Gitlab projects (ID 53).
3. Sends an email to mehtasarang17@gmail.com summarizing both lists (using variables from both listing nodes).
4. Logs "Inventory sync completed".
```

### 29. **Tiered Cloud Support**
```
Design a workflow that receives a webhook with "tier".
Tier 1: Run AWS (5) audit.
Tier 2: Run Azure (55) audit.
Tier 3: Run GCP (54) audit.
All tiers should log their respective actions and finally send a "Processing Done" email to the admin.
```

### 30. **The Ultimate Sync & Audit**
```
Build the ultimate workflow:
1. Webhook receives a security alert.
2. Check IAM full admin privileges in AWS (ID 5).
3. Check Azure admin privileges (ID 55).
4. Create Github issue (ID 50) with findings.
5. Send a high-priority email to mehtasarang17@gmail.com.
6. Log a detailed audit trail of every check's outcome.
```

---

## Testing Strategy

**🟢 Light (3-4 nodes)**: Prompts 1-10  
**🟡 Medium (5-7 nodes)**: Prompts 11-20  
**🔴 Heavy (8+ nodes)**: Prompts 21-30

---

## Expected Results
✅ **Valid Workflow JSON**: All prompts must generate engine-compatible JSON.  
✅ **Correct IDs**: AWS (5), GCP (54), Azure (55), Github (50), Gitlab (53), Email (48).  
✅ **GitHub Schema**: Uses `repo` for issue creation (not `repository`).
✅ **No Hallucinations**: Only uses the integrations listed above.
