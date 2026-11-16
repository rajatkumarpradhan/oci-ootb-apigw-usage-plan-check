# TEMPLATE ONLY - NOT plan/apply validated against a live tenancy.
# Built-in resources: OCI API Gateway gateway + deployment + usage plan + subscriber.
# Prerequisite the template does not model: each target deployment must be made
# *eligible* for usage-plan inclusion first (service-side operation).

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0"
    }
  }
}

variable "compartment_id" {
  type        = string
  description = "OCID of the compartment"
}

variable "subnet_id" {
  type        = string
  description = "OCID of a regional subnet for the gateway"
}

resource "oci_apigateway_gateway" "this" {
  compartment_id = var.compartment_id
  endpoint_type  = "PUBLIC"
  subnet_id      = var.subnet_id
  display_name   = "usage-plan-demo-gateway"
}

resource "oci_apigateway_deployment" "this" {
  compartment_id = var.compartment_id
  gateway_id     = oci_apigateway_gateway.this.id
  path_prefix    = "/orders"
  display_name   = "orders-deployment"

  specification {
    routes {
      path    = "/health"
      methods = ["GET"]
      backend {
        type = "HTTP_BACKEND"
        url  = "https://example.internal/health"
      }
    }
  }
}

resource "oci_apigateway_usage_plan" "this" {
  compartment_id = var.compartment_id
  display_name   = "partner-usage-plan"

  entitlements {
    name        = "partner-standard"
    description = "Standard partner tier"

    rate_limit {
      unit  = "SECOND"
      value = 25
    }

    quota {
      value               = 250000
      unit                = "MONTH"
      reset_policy        = "CALENDAR"
      operation_on_breach = "REJECT"
    }

    targets {
      deployment_id = oci_apigateway_deployment.this.id
    }
  }
}

resource "oci_apigateway_subscriber" "this" {
  compartment_id = var.compartment_id
  display_name   = "acme-partner"
  usage_plans    = [oci_apigateway_usage_plan.this.id]

  clients {
    name  = "acme-integration"
    token = "reporting-token-placeholder" # reporting only, NOT an auth secret
  }
}
