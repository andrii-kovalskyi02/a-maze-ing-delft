# A-maze-ing Delft

A text-based adventure/maze game set on the 2nd floor of THUAS Delft (ICT/ACS section),
built for the Applied Computer Science Q1 project by **Team ACS**.

The player wakes up in classroom 2.035 to a fire alarm, has to explore the building,
defeat the bosses guarding each area, collect four colour-coded digits and enter them
at the exit door to escape.

## Running it

Requires Python 3 and PyCharm (per the Project Guide).

```
python3 main.py
```

## Backlog

The product backlog lives in this repository's issues and on the
[A-maze-ing Delft project board](https://github.com/users/andrii-kovalskyi02/projects/1).

| Label | Meaning |
|---|---|
| `user-story` | A Product Backlog Item. One per room (US1a, US1b, ...), plus US2-US5 from the Project Guide |
| `task` | A sub-issue: concrete work under a user story |
| `enabler` | Technical work with no direct player-facing story (parser, world graph, quiz engine, persistence) |
| `process` | Scrum/course deliverables (Appendix I documents, Sprint 0 setup) |
| `question` | An open design question that needs a team or Product Owner decision |
| `area:blue` / `area:red` / `area:yellow` / `area:core` | Which part of the building, or the shared engine |

Milestones map to the sprints in the Project Guide: Sprint 1 (week 2-4, rooms only),
Sprint 2 (week 4-6, US2-US5 and persistence), Sprint 3 (week 7-8, fixes and improvements).

## Framework

Started from [SimpleMaze](https://github.com/pb12/SimpleMaze), the framework provided with
the project assignment.
