# Point-in-time entity and time evidence status

**Status:** unresolved for operational use. This is a source and local-schema assessment, not data-owner approval.

The [GUIDE publisher paper](https://arxiv.org/html/2407.09017v4) defines `Timestamp` as the time the alert was created, describes the entity columns as evidence associated with an alert, and says timestamps were noised for privacy. The [Kaggle release](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction/data) supplies the retrospective dataset. Neither source gives a separate evidence-arrival timestamp, a point-in-time field snapshot, or assurance that every entity value was available when the alert first entered a SOC queue.

The [local field audit](../outputs/entity_time_field_audit_20261114_v3.json) found one consistent alert timestamp across each composite alert's evidence rows, but this cannot prove when those rows or entity values were attached. The exploratory models use `Timestamp` plus `DeviceId`, `AccountObjectId`, `Sha256`, `IpAddress`, `NetworkMessageId`, and `EmailClusterId` from the [local sensitivity policy](../configs/entity_time_sensitivity_policy.yaml). The [official operational allowlist](../configs/field_policy.yaml) remains empty.

For a point-in-time claim, obtain a provider or SOC export with `alert_created_at`, `queue_entered_at`, `evidence_attached_at` or `field_observed_at`, revision history, and an explicit field-use decision for each entity type. Reconstruct each alert's feature view at queue entry; reject rows observed later; then rerun the frozen method and matched baseline. If only the retrospective GUIDE CSV is available, describe all entity/time results as retrospective sensitivity analysis and do not call them live-ready.

An untouched expert-ranked cohort is also absent. The prospective method and metric plan can be frozen now, but its evaluation cannot be completed from the existing GUIDE_Test labels.
