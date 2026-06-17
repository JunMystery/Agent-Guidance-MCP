---
name: healthcare-emr-patterns
description: EMR/EHR development and clinical decision support system (CDSS) patterns. Covers clinical safety, encounter workflows, prescription generation, drug interactions, dose validation, clinical scoring (NEWS2), and accessibility-first UI.
origin: Health1 Super Speciality Hospitals — contributed by Dr. Keyur Patel
version: "1.0.0"
---

# Healthcare EMR & CDSS Development Patterns

Patterns for building Electronic Medical Record (EMR) and Clinical Decision Support Systems (CDSS). Prioritizes patient safety, clinical accuracy, practitioner efficiency, and clinical audit trail compliance.

## When to Use

- Building patient encounter workflows (complaint, exam, diagnosis, prescription).
- Implementing clinical note-taking and structured template chips.
- Designing prescription/medication modules with drug interaction checking.
- Integrating Clinical Decision Support Systems (CDSS) dose validation and warning alerts.
- Implementing clinical scoring tables (NEWS2, qSOFA).
- Designing healthcare-accessible (WCAG AA) UIs for medical data entry.

## How It Works

### Patient Safety & Pure CDSS Functions

The CDSS engine is a **pure function library with zero side effects**: input clinical data, output alert arrays. This makes it highly testable.

```
EMR UI
  ↓ (user enters data)
CDSS Engine (pure functions, no side effects)
  ├── Drug Interaction Checker
  ├── Dose Validator
  ├── Clinical Scoring (NEWS2, qSOFA, etc.)
  └── Alert Classifier
  ↓ (returns alerts)
```

### 1. Drug Interaction Checking

Checks a new drug against current medications and known allergies:

```typescript
interface DrugInteractionPair {
  drugA: string;           // generic name
  drugB: string;           // generic name
  severity: 'critical' | 'major' | 'minor';
  mechanism: string;
  clinicalEffect: string;
  recommendation: string;
}

function checkInteractions(
  newDrug: string,
  currentMedications: string[],
  allergyList: string[]
): InteractionAlert[] {
  if (!newDrug) return [];
  const alerts: InteractionAlert[] = [];
  for (const current of currentMedications) {
    const interaction = findInteraction(newDrug, current);
    if (interaction) {
      alerts.push({
        severity: interaction.severity,
        pair: [newDrug, current],
        message: interaction.clinicalEffect,
        recommendation: interaction.recommendation
      });
    }
  }
  for (const allergy of allergyList) {
    if (isCrossReactive(newDrug, allergy)) {
      alerts.push({
        severity: 'critical',
        pair: [newDrug, allergy],
        message: `Cross-reactivity with documented allergy: ${allergy}`,
        recommendation: 'Do not prescribe without allergy consultation'
      });
    }
  }
  return alerts.sort((a, b) => severityOrder(a.severity) - severityOrder(b.severity));
}
```

### 2. Dose Validation

Validates a prescribed dose against weight, age, and renal-adjusted parameters:

```typescript
function validateDose(
  drug: string,
  dose: number,
  route: 'oral' | 'iv' | 'im' | 'sc' | 'topical',
  patientWeight?: number,
  patientAge?: number,
  renalFunction?: number
): DoseValidationResult {
  const rules = getDoseRules(drug, route);
  if (!rules) return { valid: true, message: 'No rules available', suggestedRange: null, factors: [] };
  const factors: string[] = [];

  // SAFETY: if rules require weight but weight missing, BLOCK
  if (rules.weightBased) {
    if (!patientWeight || patientWeight <= 0) {
      return { valid: false, message: `Weight required for ${drug}`, suggestedRange: null, factors: ['weight_missing'] };
    }
    factors.push('weight');
    const maxDose = rules.maxPerKg * patientWeight;
    if (dose > maxDose) {
      return { valid: false, message: `Dose exceeds max for ${patientWeight}kg`, suggestedRange: { min: rules.minPerKg * patientWeight, max: maxDose, unit: rules.unit }, factors };
    }
  }

  // Renal function adjustment
  if (rules.renalAdjusted && renalFunction !== undefined) {
    factors.push('renal');
    const renalMax = rules.getRenalAdjustedMax(renalFunction);
    if (dose > renalMax) {
      return { valid: false, message: `Exceeds renal-adjusted max for eGFR ${renalFunction}`, suggestedRange: { min: rules.typicalMin, max: renalMax, unit: rules.unit }, factors };
    }
  }

  return { valid: true, message: 'Within range', suggestedRange: { min: rules.typicalMin, max: rules.typicalMax, unit: rules.unit }, factors };
}
```

### 3. Clinical Scoring: NEWS2

```typescript
interface NEWS2Input {
  respiratoryRate: number; oxygenSaturation: number; supplementalOxygen: boolean;
  temperature: number; systolicBP: number; heartRate: number;
  consciousness: 'alert' | 'voice' | 'pain' | 'unresponsive';
}
```
Auto-calculates the clinical score and returns a result with risk levels and ICU escalation alerts.

### 4. Alert Severity and UI Behavior

| Severity | UI Behavior | Clinician Action Required |
|----------|-------------|--------------------------|
| Critical | Block action. Non-dismissable modal. Red. | Must document override reason to proceed |
| Major | Warning banner inline. Orange. | Must acknowledge before proceeding |
| Minor | Info note inline. Yellow. | Awareness only, no action required |

*Never use dismissable toasts for critical alerts. Log all alerts and override reasons in the audit trail.*

---

## EMR UI & Accessibility Patterns

- **Single-Page Encounter Flow**: Vertically scrollable single page (Header, Chief Complaint, Vitals, Diagnosis, Medications, Lock/Sign) to prevent context fragmentation.
- **Encounter Locking**: Signed encounter notes are write-protected and immutable. Corrections must be added as linked Addendum records.
- **Accessibility**:
  - Minimum contrast 4.5:1 (WCAG AA).
  - large touch targets (44x44px minimum).
  - No color-only status indicators.

## See Also

- Skill: `accessibility`
- Skill: `error-handling`
- Skill: `unified-notifications-ops`
