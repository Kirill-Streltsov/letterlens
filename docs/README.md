# Documentation

The documents follow the rules of ASD-STE100 Simplified Technical English where
practical: short sentences, active voice, one instruction per step, one term per concept.

| Document | Read it to |
|---|---|
| [LetterLens-Guide.pdf](LetterLens-Guide.pdf) | Understand everything in one illustrated guide (rebuild: `python3 docs/guide/build.py`) |
| [operations/deployment.md](operations/deployment.md) | Deploy to production (manual steps) |
| [operations/custom-domain.md](operations/custom-domain.md) | Use an own domain instead of the CloudFront address |
| [development.md](development.md) | Run, test and change the code locally |
| [architecture/overview.md](architecture/overview.md) | Understand the system |
| [architecture/adr/](architecture/adr/) | Understand why each main decision was made |
| [ai/pipeline.md](ai/pipeline.md) | Understand the AI steps, prompts and gateway |
| [ai/evaluation.md](ai/evaluation.md) | Measure quality and run the release gate |
| [security/threat-model.md](security/threat-model.md) | See threats, mitigations and tests |
| [security/data-protection.md](security/data-protection.md) | Prepare the privacy policy and the DPIA |
| [legal/rdg-boundary.md](legal/rdg-boundary.md) | Prepare the legal review |
| [operations/runbook.md](operations/runbook.md) | Respond to alarms and do routine tasks |
| [operations/cost.md](operations/cost.md) | Understand the free limits and the cost at scale |
| [api.md](api.md) | Use the API |

## Terms

| Term | Meaning |
|---|---|
| Reader | A person who receives a letter and uses the app |
| Counsellor | A person in a counselling service who receives shared letters |
| Tenant | A counselling service or an employer in LetterLens |
| Share | A reader's consent to show one letter to one tenant, with an expiry |
| Verified | A date or amount that the code found in the cited line of the letter |
| Please check (`needs_check`) | A date or amount that the code could not confirm, or an estimate |
| Degraded | A result made with rules only, because the model was not available |
| KEK, DEK | Key encryption key (one, held by the service); data encryption key (one per user) |
