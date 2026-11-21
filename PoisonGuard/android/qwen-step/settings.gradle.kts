pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("D:/NCKH/MobileSYS/MobileFineTuner/android-visualizer/mft-sdk/build/repo") }
    }
}

rootProject.name = "PoisonGuardQwenStep"
include(":app")
