package com.poisonguard.qwenstep

import android.os.Bundle
import android.util.Log
import android.app.Activity
import android.widget.TextView
import com.mobilefinetuner.sdk.MobileFineTuner
import java.io.File
import kotlin.system.measureTimeMillis

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val textView = TextView(this)
        setContentView(textView)

        Thread {
            val modelDir = File(getExternalFilesDir(null), "models/Qwen2.5-0.5B")
            val configFile = File(modelDir, "config.json")
            Log.i(TAG, "modelDir=${modelDir.absolutePath} exists=${modelDir.exists()} files=${modelDir.listFiles()?.size} configExists=${configFile.exists()} configCanRead=${configFile.canRead()}")
            val message = try {
                runStep(modelDir, textView)
            } catch (e: Exception) {
                Log.e(TAG, "training step failed", e)
                "FAILED: ${e}"
            }
            runOnUiThread { textView.text = message }
        }.start()
    }

    private fun runStep(modelDir: File, textView: TextView): String {
        val seqLen = 8
        val batch = 1
        val inputIds = IntArray(batch * seqLen) { (it % 100) + 1 }
        val attentionMask = FloatArray(batch * seqLen) { 1f }
        val labels = inputIds.copyOf()

        val mf = MobileFineTuner.open(modelDir.absolutePath, true)
        mf.initLora(MobileFineTuner.LoraConfig.attentionQkvo())
        mf.createTrainer(MobileFineTuner.TrainerConfig.defaults())

        val stepTimes = mutableListOf<Long>()
        var lastLoss = 0f
        repeat(5) { index ->
            var loss = 0f
            val ms = measureTimeMillis {
                val result = mf.trainStep(inputIds, attentionMask, labels, batch, seqLen)
                loss = result.loss
            }
            lastLoss = loss
            stepTimes += ms
            Log.i(TAG, "step ${index + 1}/5 loss=$loss time=${ms}ms")
        }
        mf.close()

        val rssKb = readRssKb()
        val msg = "Qwen pilot OK: lastLoss=$lastLoss, times=$stepTimes, RSS=${rssKb}KB"
        Log.i(TAG, msg)
        return msg
    }

    private fun readRssKb(): Long {
        return try {
            File("/proc/self/statm").readText().split(" ")[1].toLong() * 4
        } catch (_: Exception) {
            -1
        }
    }

    companion object {
        private const val TAG = "PoisonGuardQwenStep"
    }
}
