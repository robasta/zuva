package com.sunsynk.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.sunsynk.mobile.ui.MainUiState
import com.sunsynk.mobile.ui.MainViewModel
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel = koinViewModel()) {
    val state = viewModel.uiState
    val snackbarHostState = remember { SnackbarHostState() }
    val coroutineScope = rememberCoroutineScope()

    Scaffold(snackbarHost = { SnackbarHost(hostState = snackbarHostState) }) { paddingValues ->
        val currentState = state.value
        when (currentState) {
            MainUiState.LoggedOut -> LoginForm(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                onLogin = { username, password -> viewModel.login(username, password) }
            )
            MainUiState.Loading -> LoadingScreen(modifier = Modifier.padding(paddingValues))
            MainUiState.LoggedIn -> DashboardPlaceholder(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                onLogout = { viewModel.logout() }
            )
            is MainUiState.Error -> {
                LaunchedEffect(currentState.message) {
                    coroutineScope.launch {
                        snackbarHostState.showSnackbar(currentState.message)
                    }
                }
                LoginForm(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues),
                    onLogin = { username, password -> viewModel.login(username, password) }
                )
            }
        }
    }
}

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
    val context = LocalContext.current
    val username = remember { mutableStateOf("demo") }
    val password = remember { mutableStateOf("demo123") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = stringResource(id = R.string.login_title), style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(
            value = username.value,
            onValueChange = { username.value = it },
            label = { Text("Username") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        )
        OutlinedTextField(
            value = password.value,
            onValueChange = { password.value = it },
            label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        )
        Button(
            modifier = Modifier.padding(top = 16.dp),
            onClick = { onLogin(username.value, password.value) }
        ) {
            Text(text = "Sign in")
        }
    }
}

@Composable
private fun DashboardPlaceholder(
    modifier: Modifier = Modifier,
    onLogout: () -> Unit
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(text = stringResource(id = R.string.dashboard_greeting), style = MaterialTheme.typography.headlineMedium)
        Button(
            modifier = Modifier.padding(top = 24.dp),
            onClick = onLogout
        ) {
            Text(text = "Sign out")
        }
    }
}
