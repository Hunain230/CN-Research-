"""Assemble the template-required single TeX manuscript from editable sections."""
from pathlib import Path
import re

root=Path(__file__).resolve().parent
parts=[
 ('introduction','Introduction','section'),
 ('related_work','Related work','section'),
 ('problem_formulation','Proposed methodology','section'),
 ('agent_framework','Agent framework and executable contracts','subsection'),
 ('architecture','Architecture and data flow','subsection'),
 ('methodology','Evidence verification and endpoint fallback','subsection'),
 ('experimental_design','Experimental setup','section'),
 ('metrics','Evaluation metrics','subsection'),
 ('results','Results and analysis','section'),
 ('base_comparison','Comparison with base papers and state of the art','section'),
 ('ablation','Ablation study','section'),
 ('discussion','Discussion','section'),
 ('threats_to_validity','Threats to validity','subsection'),
 ('real_world_readiness','External evaluation readiness','subsection'),
 ('conclusion','Conclusion and future work','section'),
 ('declarations','Declarations and acknowledgements','section'),
]

title='A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization'
abstract=('Security operations centers need to reconstruct incidents from fragmented alerts and prioritize review '
'without mistaking copied, late, or contradictory evidence for independent corroboration. This study specifies '
'a bounded correlation (C), prioritization (P), and verification (V) agent framework, implements offline role '
'contracts and a small local Qwen prototype, and separately evaluates a deterministic provenance-constrained '
'C/V/P realization. These tracks have distinct populations and cannot be pooled. On a fresh controlled synthetic '
'holdout of 15 queues and 5,018 eligible alerts, a frozen endpoint fallback increased Incident Recall@20 from '
'250/300 (83.33\\%) to 260/300 (86.67\\%), recoverability from 263/300 (87.67\\%) to 281/300 '
'(93.67\\%), and P@10 from 107/150 (71.33\\%) to 113/150 (75.33\\%), with zero observed false '
'grouped pairs in either arm. A post-seal audit found 711 genuine accepted relationship tokens, zero false '
'accepts, 35 genuine rejections, and 150 false rejections. The candidate missed its development gate by one '
'incident; an unchanged fresh-holdout test followed a documented protocol decision. On a separate retrospective '
'GUIDE track, the full-queue statistical reference achieved 49.82\\% Recall@20 on 499 queues. The local '
'LLM prototype does not establish an LLM performance advantage. GUIDE lacks the provenance and arrival-time '
'fields needed for external evaluation of the frozen verifier; operational efficacy remains unmeasured.')

head=r'''% Springer Nature manuscript source, generated from the editable sections in this folder.
% Template version 3.1 (December 2024); no margin, font or spacing overrides.
\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}
\usepackage{graphicx}
\usepackage{booktabs,tabularx,array}
\usepackage{amsmath,amssymb}
\usepackage{microtype}
\usepackage[title]{appendix}
\graphicspath{{figures/}}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcommand{\tabhead}[1]{\textbf{#1}}
\newcommand{\gaincell}[1]{#1}
\hypersetup{pdftitle={A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization},pdfauthor={Hunain Shahid and Hammad Ullah Khan}}
\begin{document}
\title[A Multi-Agent LLM Framework for SOC Threat Correlation]{A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization}
\author*[1]{\fnm{Hunain} \sur{Shahid}}\email{i240127@nu.edu.pk}
\author[1]{\fnm{Hammad Ullah} \sur{Khan}}\email{i242539@nu.edu.pk}
\affil*[1]{\orgdiv{Department of Computer Science}, \orgname{National University of Computer and Emerging Sciences (FAST-NUCES)}, \orgaddress{\city{Islamabad}, \country{Pakistan}}}
\abstract{'''+abstract+r'''}
\keywords{security operations center, alert correlation, large language models, evidence provenance, multi-agent systems, incident prioritization}
\maketitle
'''

def transform(name, heading, level):
    s=(root/'sections'/f'{name}.tex').read_text(encoding='utf-8')
    m=re.search(r'\\section\{[^}]+\}(?:\\label\{[^}]+\})?',s)
    if not m: raise ValueError(name+' missing section')
    if level=='subsection':
        s=s.replace(r'\subsection{',r'\subsubsection{')
    old_label=re.search(r'\\label\{[^}]+\}',m.group(0))
    s=s[:m.start()]+f'\\{level}{{{heading}}}'+(old_label.group(0) if old_label else '')+s[m.end():]
    s=s.replace(r'\begin{figure*}',r'\begin{figure}').replace(r'\end{figure*}',r'\end{figure}')
    s=s.replace(r'\begin{table*}',r'\begin{table}').replace(r'\end{table*}',r'\end{table}')
    return s

body='\n\n'.join(transform(*p) for p in parts)
# The short submission version retains six reader-scale figures and six centered
# tables. The fuller editable research account stays in sections/ for expansion.
drop_labels={'fig:pipeline','fig:groups','fig:provenance','fig:safety','fig:decomp',
             'tab:notation','tab:decisions','tab:cohorts','tab:development','tab:readiness'}
for kind in ('figure','table'):
    pattern=r'\\begin\{'+kind+r'\}(?:\[[^]]*\])?.*?\\end\{'+kind+r'\}'
    body=re.sub(pattern,lambda m:'' if any('\\label{'+k+'}' in m.group(0) for k in drop_labels) else m.group(0),body,flags=re.S)
for k,phrase in {'fig:pipeline':'the data-flow summary','fig:groups':'the grouping/retrieval distinction',
                 'fig:provenance':'the evidence-timing example','fig:safety':'the all-group safety audit',
                 'fig:decomp':'the retrieval decomposition','tab:decisions':'the logical decision cases',
                 'tab:development':'the separate development studies'}.items():
    body=re.sub(r'(?:Figure|Fig\.|Table)~\\ref\{'+re.escape(k)+r'\}',phrase,body)
for figure in ('architecture','agent_contracts','verification_methodology','phase33_results','queue_delta_heatmap'):
    body=re.sub(r'\\includegraphics\[width=[^]]+\](?=\{figures/'+figure+r'\.pdf\})',
                lambda _:r'\includegraphics[width=\textwidth]',body)
full=head+'\n'+body+'\n\\bibliography{references}\n\\end{document}\n'
(root/'main.tex').write_text(full,encoding='utf-8')
print('Wrote main.tex:',len(full.split()),'words')
