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
 ('reproducibility','Dataset, parameters, and reproducibility','subsection'),
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
abstract=('A SOC analyst has to decide which alerts describe the same incident before deciding what to inspect first. '
'That decision can be distorted by copied observations, late-arriving evidence, and claims that disagree about '
'an endpoint. We specify bounded correlation (C), prioritization (P), and verification (V) agent roles and test '
'their software contracts with an offline adapter and a small local Qwen prototype. The measured experiment is '
'separate: a frozen, deterministic C/V/P pipeline with a provenance gate. On a fresh synthetic holdout of 15 '
'queues and 5,018 eligible alerts, its endpoint fallback raised incident Recall@20 from 250/300 (83.33\\%) '
'to \\textbf{260/300 (86.67\\%)}, recoverability from 263/300 (87.67\\%) to \\textbf{281/300 (93.67\\%)}, and P@10 '
'from 107/150 (71.33\\%) to \\textbf{113/150 (75.33\\%)}. Neither arm formed a false grouped pair under simulator '
'truth. After prediction files were sealed, an audit found 711 accepted genuine relationship tokens, no accepted '
'false tokens, 35 genuine rejections, and 150 false rejections. The candidate had missed its development gate '
'by one incident; testing it unchanged on the fresh holdout followed a documented protocol adjustment. A separate '
'retrospective GUIDE reference reached 49.82\\% Recall@20 on 499 queues. The local LLM run does not establish '
'a model advantage, and the available GUIDE export lacks the original roots and evidence-arrival times required '
'to test the frozen verifier on operational data.')

head=r'''% Springer Nature manuscript source, generated from the editable sections in this folder.
% Template version 3.1 (December 2024); no margin, font or spacing overrides.
\documentclass[pdflatex,sn-mathphys-num,iicol]{sn-jnl}
\usepackage{graphicx}
\usepackage{booktabs,tabularx,array}
\usepackage{amsmath,amssymb}
\usepackage{microtype}
\usepackage[title]{appendix}
\graphicspath{{figures/}}
% Allow compact, single-column floats to occupy available page space.
\setcounter{topnumber}{3}
\setcounter{bottomnumber}{2}
\setcounter{totalnumber}{5}
\setcounter{dbltopnumber}{3}
\renewcommand{\floatpagefraction}{.62}
\renewcommand{\dblfloatpagefraction}{.65}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcommand{\tabhead}[1]{\textbf{#1}}
\newcommand{\gaincell}[1]{\textbf{#1}}
\hypersetup{pdftitle={A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization},pdfauthor={Hunain Shahid and Hammad Ullah Khan}}
\begin{document}
\title[A Multi-Agent LLM Framework for SOC Threat Correlation]{A Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization}
\author*[1]{\fnm{Hunain} \sur{Shahid}}\email{i240127@nu.edu.pk}
\author[1]{\fnm{Hammad Ullah} \sur{Khan}}\email{i242539@nu.edu.pk}
\affil*[1]{\orgdiv{Department of Artificial Intelligence and Data Science}, \orgname{National University of Computer and Emerging Sciences (FAST-NUCES)}, \orgaddress{\city{Islamabad}, \country{Pakistan}}}
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
    s=re.sub(r'\\begin\{(figure|table)(\*)?\}(?:\[[^]]*\])?',
             lambda m:r'\begin{'+m.group(1)+(m.group(2) or '')+r'}'+
             ('[!tbp]' if m.group(2) else '[!htbp]'),s)
    return s

body='\n\n'.join(transform(*p) for p in parts)
# Keep the main account focused; extended investigations remain in sections/.
drop_labels={'fig:pipeline','fig:groups','fig:provenance','fig:safety',
             'tab:notation','tab:decisions','tab:cohorts','tab:development','tab:readiness'}
for kind in ('figure','table'):
    pattern=r'\\begin\{'+kind+r'\*?\}(?:\[[^]]*\])?.*?\\end\{'+kind+r'\*?\}'
    body=re.sub(pattern,lambda m:'' if any('\\label{'+k+'}' in m.group(0) for k in drop_labels) else m.group(0),body,flags=re.S)
for k,phrase in {'fig:pipeline':'the data-flow summary','fig:groups':'the grouping/retrieval distinction',
                 'fig:provenance':'the evidence-timing example','fig:safety':'the all-group safety audit',
                 'tab:decisions':'the logical decision cases',
                 'tab:development':'the separate development studies'}.items():
    body=re.sub(r'(?:Figure|Fig\.|Table)~\\ref\{'+re.escape(k)+r'\}',phrase,body)
full=head+'\n'+body+'\n\\bibliography{references}\n\\end{document}\n'
(root/'main.tex').write_text(full,encoding='utf-8')
print('Wrote main.tex:',len(full.split()),'words')
