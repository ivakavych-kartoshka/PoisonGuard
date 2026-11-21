package com.poisonguard.service

import android.content.Context
import com.mobilefinetuner.sdk.MobileFineTuner
import java.io.File
import java.security.MessageDigest

/**
 * Skeleton service. It is not production-ready and intentionally keeps all
 * policy decisions explicit.
 */
class MobileFineTunerTrainingService(
    private val context: Context,
    private val modelDir: File,
) {
    private val policy = PoisonGuardPolicy()

    fun trainEligibleEvent(
        event: ProvenanceEvent,
        inputIds: IntArray,
        attentionMask: IntArray,
        labels: IntArray,
        batchSize: Int,
        sequenceLength: Int,
    ): TrainingStepResult {
        val memoryDecision = policy.decideMemory(event)
        val trainingDecision = policy.decideTraining(event)

        if (trainingDecision == SinkDecision.DENY) {
            return TrainingStepResult(
                eventId = event.eventId,
                loss = 0f,
                checkpointHash = "",
                promoted = false,
                message = "training denied by provenance policy",
            )
        }

        // TODO: open the model once and cache it; this skeleton opens per call.
        val mf = MobileFineTuner.open(modelDir, true)
        mf.initLora(MobileFineTuner.LoraConfig.attentionQkvo())
        mf.createTrainer(MobileFineTuner.TrainerConfig.defaults())

        val result = mf.trainStep(
            inputIds,
            attentionMask,
            labels,
            batchSize,
            sequenceLength,
        )

        // TODO: persist adapter/checkpoint to a versioned directory and hash it.
        val checkpointHash = sha256("candidate-${event.eventId}-${result.loss}")
        val promoted = trainingDecision == SinkDecision.ALLOW

        mf.close()

        return TrainingStepResult(
            eventId = event.eventId,
            loss = result.loss,
            checkpointHash = checkpointHash,
            promoted = promoted,
            message = "memory=$memoryDecision, training=$trainingDecision",
        )
    }

    /**
     * Minimal service loop. Production code must persist lineage and apply
     * rollback/replay outside this loop.
     */
    fun trainEligibleEvents(
        events: List<ProvenanceEvent>,
        inputIds: IntArray,
        attentionMask: IntArray,
        labels: IntArray,
        batchSize: Int,
        sequenceLength: Int,
    ): List<TrainingStepResult> {
        val results = mutableListOf<TrainingStepResult>()
        for (event in events) {
            results += trainEligibleEvent(
                event = event,
                inputIds = inputIds,
                attentionMask = attentionMask,
                labels = labels,
                batchSize = batchSize,
                sequenceLength = sequenceLength,
            )
        }
        return results
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(value.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}
