package com.poisonguard.service

enum class SinkDecision { ALLOW, QUARANTINE, DENY }

/**
 * Illustrative policy only. Deployments must validate these choices.
 */
class PoisonGuardPolicy {
    fun decideMemory(event: ProvenanceEvent): SinkDecision =
        when (event.channel) {
            "typed" -> SinkDecision.ALLOW
            else -> SinkDecision.QUARANTINE
        }

    fun decideTraining(event: ProvenanceEvent): SinkDecision =
        when (event.channel) {
            "typed" -> SinkDecision.ALLOW
            else -> SinkDecision.DENY
        }

    fun leastTrustInheritance(parentDecisions: List<SinkDecision>): SinkDecision =
        if (parentDecisions.any { it == SinkDecision.DENY }) SinkDecision.DENY
        else if (parentDecisions.any { it == SinkDecision.QUARANTINE }) SinkDecision.QUARANTINE
        else SinkDecision.ALLOW
}
