package com.example.shoplog

import android.content.Context
import java.io.File

/** One CSV file in the app's private storage. Same columns as the Google Sheets templates. */
class CsvFile(context: Context, name: String, private val header: List<String>) {
    private val file = File(context.filesDir, name)

    fun append(row: List<String>) {
        require(row.size == header.size) { "expected ${header.size} fields, got ${row.size}" }
        if (!file.exists()) file.writeText(header.joinToString(",") + "\n")
        file.appendText(row.joinToString(",") { escape(it) } + "\n")
    }

    /** Data rows only (header dropped), oldest first. */
    fun rows(): List<List<String>> {
        if (!file.exists()) return emptyList()
        return parse(file.readText()).drop(1)
    }

    /** The whole file as text, ready to share or paste into a sheet. */
    fun text(): String = if (file.exists()) file.readText() else header.joinToString(",") + "\n"

    companion object {
        val DAILY_HEADER = listOf(
            "date", "phase", "walk_ins", "bills", "sales_rs", "exchanges", "festival",
            "src_google", "src_whatsapp", "src_instagram", "src_friend", "src_passing", "src_other", "notes",
        )
        val LOST_HEADER = listOf(
            "date", "item_wanted", "size", "price_expected_rs", "bought_instead", "reason_code", "notes",
        )

        fun escape(field: String): String =
            if (field.any { it == ',' || it == '"' || it == '\n' || it == '\r' }) {
                "\"" + field.replace("\"", "\"\"") + "\""
            } else {
                field
            }

        fun parse(text: String): List<List<String>> {
            val rows = mutableListOf<List<String>>()
            var row = mutableListOf<String>()
            val field = StringBuilder()
            var inQuotes = false
            var i = 0
            while (i < text.length) {
                val c = text[i]
                when {
                    inQuotes && c == '"' && i + 1 < text.length && text[i + 1] == '"' -> {
                        field.append('"')
                        i++
                    }
                    c == '"' -> inQuotes = !inQuotes
                    !inQuotes && c == ',' -> {
                        row.add(field.toString())
                        field.setLength(0)
                    }
                    !inQuotes && c == '\n' -> {
                        row.add(field.toString())
                        field.setLength(0)
                        rows.add(row)
                        row = mutableListOf()
                    }
                    !inQuotes && c == '\r' -> Unit
                    else -> field.append(c)
                }
                i++
            }
            if (field.isNotEmpty() || row.isNotEmpty()) {
                row.add(field.toString())
                rows.add(row)
            }
            return rows
        }
    }
}
