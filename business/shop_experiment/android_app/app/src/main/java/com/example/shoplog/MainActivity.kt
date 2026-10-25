package com.example.shoplog

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import java.time.LocalDate

private val REASON_CODES = listOf(
    "PRICE", "SIZE", "STYLE", "COLOUR", "STOCK", "QUALITY", "JUST_LOOKING", "OTHER",
)

private val SOURCES = listOf(
    "src_google" to "Google",
    "src_whatsapp" to "WhatsApp",
    "src_instagram" to "Instagram",
    "src_friend" to "Friend",
    "src_passing" to "Passing by",
    "src_other" to "Other",
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val daily = CsvFile(applicationContext, "daily_log.csv", CsvFile.DAILY_HEADER)
        val lost = CsvFile(applicationContext, "lost_sales.csv", CsvFile.LOST_HEADER)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    ShopLogApp(daily, lost)
                }
            }
        }
    }
}

@Composable
private fun ShopLogApp(daily: CsvFile, lost: CsvFile) {
    var tab by remember { mutableIntStateOf(0) }
    Column(modifier = Modifier.safeDrawingPadding()) {
        TabRow(selectedTabIndex = tab) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("Daily log") })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("Lost sale") })
        }
        if (tab == 0) DailyLogScreen(daily) else LostSaleScreen(lost)
    }
}

private fun String.digitsOrZero(): String = filter { it.isDigit() }.ifEmpty { "0" }

private fun share(context: Context, subject: String, csv: String) {
    val send = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_SUBJECT, subject)
        putExtra(Intent.EXTRA_TEXT, csv)
    }
    context.startActivity(Intent.createChooser(send, subject))
}

@Composable
private fun DailyLogScreen(csv: CsvFile) {
    val context = LocalContext.current
    var refresh by remember { mutableIntStateOf(0) }
    var phase by remember { mutableStateOf("baseline") }
    var walkIns by remember { mutableStateOf("") }
    var bills by remember { mutableStateOf("") }
    var sales by remember { mutableStateOf("") }
    var exchanges by remember { mutableStateOf("") }
    var festival by remember { mutableStateOf(false) }
    val sources = remember { mutableStateMapOf<String, String>() }
    var notes by remember { mutableStateOf("") }
    val recent = remember(refresh) { csv.rows().takeLast(7).reversed() }

    Column(
        modifier = Modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Fill at closing time", style = MaterialTheme.typography.titleMedium)
        OutlinedTextField(phase, { phase = it }, label = { Text("Phase") }, modifier = Modifier.fillMaxWidth())
        NumberField("Walk-ins", walkIns) { walkIns = it }
        NumberField("Bills", bills) { bills = it }
        NumberField("Sales (Rs)", sales) { sales = it }
        NumberField("Exchanges", exchanges) { exchanges = it }
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text("Festival day", modifier = Modifier.weight(1f))
            Switch(checked = festival, onCheckedChange = { festival = it })
        }
        Text("How did buyers find us? (count)", style = MaterialTheme.typography.titleSmall)
        SOURCES.forEach { (key, label) ->
            NumberField(label, sources[key] ?: "") { sources[key] = it }
        }
        OutlinedTextField(notes, { notes = it }, label = { Text("Notes") }, modifier = Modifier.fillMaxWidth())

        Button(
            modifier = Modifier.fillMaxWidth(),
            onClick = {
                val row = listOf(
                    LocalDate.now().toString(),
                    phase.trim(),
                    walkIns.digitsOrZero(),
                    bills.digitsOrZero(),
                    sales.digitsOrZero(),
                    exchanges.digitsOrZero(),
                    if (festival) "yes" else "no",
                ) + SOURCES.map { (key, _) -> (sources[key] ?: "").digitsOrZero() } + notes.trim()
                csv.append(row)
                walkIns = ""; bills = ""; sales = ""; exchanges = ""; festival = false
                sources.clear(); notes = ""
                refresh++
            },
        ) { Text("Save today") }

        OutlinedButton(
            modifier = Modifier.fillMaxWidth(),
            onClick = { share(context, "Shop daily log", csv.text()) },
        ) { Text("Share all as CSV") }

        Text("Last 7 entries", style = MaterialTheme.typography.titleSmall)
        if (recent.isEmpty()) Text("Nothing saved yet.")
        recent.forEach { r ->
            Text("${r.getOrElse(0) { "" }}: ${r.getOrElse(2) { "0" }} walk-ins, ${r.getOrElse(3) { "0" }} bills, Rs ${r.getOrElse(4) { "0" }}")
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LostSaleScreen(csv: CsvFile) {
    val context = LocalContext.current
    var refresh by remember { mutableIntStateOf(0) }
    var item by remember { mutableStateOf("") }
    var size by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var boughtInstead by remember { mutableStateOf("nothing") }
    var reason by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    val recent = remember(refresh) { csv.rows().takeLast(7).reversed() }

    Column(
        modifier = Modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Fill after each walk-out", style = MaterialTheme.typography.titleMedium)
        OutlinedTextField(item, { item = it }, label = { Text("Item wanted") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(size, { size = it }, label = { Text("Size") }, modifier = Modifier.fillMaxWidth())
        NumberField("Price expected (Rs)", price) { price = it }
        OutlinedTextField(
            boughtInstead, { boughtInstead = it },
            label = { Text("Bought instead") }, modifier = Modifier.fillMaxWidth(),
        )
        Text("Why did they not buy?", style = MaterialTheme.typography.titleSmall)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            REASON_CODES.forEach { code ->
                FilterChip(selected = reason == code, onClick = { reason = code }, label = { Text(code) })
            }
        }
        OutlinedTextField(notes, { notes = it }, label = { Text("Notes") }, modifier = Modifier.fillMaxWidth())

        Button(
            modifier = Modifier.fillMaxWidth(),
            enabled = item.isNotBlank() && reason.isNotEmpty(),
            onClick = {
                csv.append(
                    listOf(
                        LocalDate.now().toString(),
                        item.trim(),
                        size.trim(),
                        price.digitsOrZero(),
                        boughtInstead.trim().ifEmpty { "nothing" },
                        reason,
                        notes.trim(),
                    ),
                )
                item = ""; size = ""; price = ""; boughtInstead = "nothing"; reason = ""; notes = ""
                refresh++
            },
        ) { Text("Save lost sale") }

        OutlinedButton(
            modifier = Modifier.fillMaxWidth(),
            onClick = { share(context, "Shop lost sales", csv.text()) },
        ) { Text("Share all as CSV") }

        Text("Last 7 entries", style = MaterialTheme.typography.titleSmall)
        if (recent.isEmpty()) Text("Nothing saved yet.")
        recent.forEach { r ->
            Text("${r.getOrElse(0) { "" }}: ${r.getOrElse(1) { "" }} (${r.getOrElse(5) { "" }})")
        }
    }
}

@Composable
private fun NumberField(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
}
