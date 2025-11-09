{{- define "semantic-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "semantic-service.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "semantic-service.labels" -}}
app.kubernetes.io/name: {{ include "semantic-service.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: Helm
{{- end -}}

{{- define "semantic-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "semantic-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
