package com.sunsynk.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.sunsynk.mobile.ui.MainUiState
import com.sunsynk.mobile.ui.MainViewModel
import com.sunsynk.mobile.ui.alerts.AlertsScreen
import com.sunsynk.mobile.ui.dashboard.DashboardScreen
import com.sunsynk.mobile.ui.dashboard.DashboardViewModel
import com.sunsynk.mobile.ui.theme.SunsynkDashboardTheme
import kotlinx.coroutines.launch
import org.koin.androidx.compose.koinViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SunsynkDashboardTheme {
                MainScreen()
            }
        }
    }
}

@Composable
fun MainScreen(
    mainViewModel: MainViewModel = koinViewModel(),
    dashboardViewModel: DashboardViewModel = koinViewModel()
) {
    val state by mainViewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    if (state == MainUiState.Authenticated) {
        AuthenticatedHome(
            dashboardViewModel = dashboardViewModel,
            onLogout = { mainViewModel.logout() }
        )
    } else {
        Scaffold(snackbarHost = { SnackbarHost(hostState = snackbarHostState) }) { paddingValues ->
            when (state) {
                MainUiState.Unauthenticated -> LoginForm(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    onLogin = { username, password -> mainViewModel.login(username, password) }
                )
                MainUiState.Loading -> LoadingScreen(modifier = Modifier.padding(paddingValues))
                is MainUiState.Error -> {
                    val errorState = state as MainUiState.Error
                    LaunchedEffect(errorState.message) {
                        coroutineScope.launch {
                            snackbarHostState.showSnackbar(errorState.message)
                        }
                    }
                    LoginForm(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(paddingValues),
                        onLogin = { username, password -> mainViewModel.login(username, password) }
                    )
                }
                MainUiState.Authenticated -> Unit
            }
        }
    }
}

private enum class MainDestination { DASHBOARD, ALERTS }

@Composable
private fun LoadingScreen(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator()
        Text(
            text = stringResource(id = R.string.loading_message),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 16.dp)
        )
    }
}

@Composable
private fun LoginForm(
    modifier: Modifier = Modifier,
    onLogin: (String, String) -> Unit
) {
    var username by rememberSaveable { mutableStateOf("demo") }
    var password by rememberSaveable { mutableStateOf("demo123") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = stringResource(id = R.string.login_title), style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("Username") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        )
        Button(
            modifier = Modifier.padding(top = 16.dp),
            onClick = { onLogin(username, password) }
        ) {
            Text(text = "Sign in")
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AuthenticatedHome(
    dashboardViewModel: DashboardViewModel,
    onLogout: () -> Unit
) {
    val destinations = listOf(MainDestination.DASHBOARD, MainDestination.ALERTS)
    val snackbarHostState = remember { SnackbarHostState() }
    var currentDestination by remember { mutableStateOf(MainDestination.DASHBOARD) }

    Scaffold(
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    val titleRes = when (currentDestination) {
                        MainDestination.DASHBOARD -> R.string.tab_dashboard
                        MainDestination.ALERTS -> R.string.tab_alerts
                    }
                    Text(text = stringResource(id = titleRes))
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(imageVector = Icons.Default.Logout, contentDescription = stringResource(id = R.string.dashboard_logout))
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar {
                destinations.forEach { destination ->
                    val labelRes = when (destination) {
                        MainDestination.DASHBOARD -> R.string.tab_dashboard
                        MainDestination.ALERTS -> R.string.tab_alerts
                    }
                    val icon = when (destination) {
                        MainDestination.DASHBOARD -> Icons.Default.Home
                        MainDestination.ALERTS -> Icons.Default.Notifications
                    }
                    NavigationBarItem(
                        selected = currentDestination == destination,
                        onClick = { currentDestination = destination },
                        icon = { Icon(imageVector = icon, contentDescription = stringResource(id = labelRes)) },
                        label = { Text(text = stringResource(id = labelRes)) }
                    )
                }
            }
        }
    ) { paddingValues ->
        Box(modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
        ) {
            when (currentDestination) {
                MainDestination.DASHBOARD -> DashboardScreen(
                    modifier = Modifier.fillMaxSize(),
                    viewModel = dashboardViewModel
                )
                MainDestination.ALERTS -> AlertsScreen(
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }
}
