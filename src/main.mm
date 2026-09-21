#import <Cocoa/Cocoa.h>
#include "parser.hpp"
#include "shell.hpp"
#include "vfs.hpp"
#include <fstream>
#include <unistd.h>

@interface EmulatorApp : NSObject <NSApplicationDelegate, NSTextFieldDelegate>
@property (strong) NSWindow *window;
@property (strong) NSTextView *terminalView;
@property (strong) NSTextField *inputField;
@property (assign) VirtualFileSystem *vfs;
@property (assign) ShellEmulator *shell;
@property (strong) NSString *scriptPath;
@end

@implementation EmulatorApp

- (void)appendOutput:(NSString *)text {
    dispatch_async(dispatch_get_main_queue(), ^{
        NSString *line = [text stringByAppendingString:@"\n"];
        NSDictionary *attrs = @{
            NSForegroundColorAttributeName: [NSColor greenColor],
            NSFontAttributeName: [NSFont fontWithName:@"Menlo" size:13] ?: [NSFont monospacedSystemFontOfSize:13 weight:NSFontWeightRegular]
        };
        NSAttributedString *attrStr = [[NSAttributedString alloc] initWithString:line attributes:attrs];
        [self.terminalView.textStorage appendAttributedString:attrStr];
        [self.terminalView scrollRangeToVisible:NSMakeRange(self.terminalView.string.length, 0)];
    });
}

- (void)executeCommand:(NSString *)rawCmd {
    std::string line = [rawCmd UTF8String];
    auto tokens = CommandParser::tokenize(line);
    if (tokens.empty()) return;

    std::string cmd = tokens[0];
    std::vector<std::string> args(tokens.begin() + 1, tokens.end());
    auto [out, isExit] = self.shell->execute(cmd, args);

    if (isExit) {
        [NSApp terminate:nil];
    } else if (!out.empty()) {
        [self appendOutput:[NSString stringWithUTF8String:out.c_str()]];
    }
}

- (void)controlTextDidEndEditing:(NSNotification *)obj {
    if ([[[obj userInfo] objectForKey:@"NSTextMovement"] intValue] == NSReturnTextMovement) {
        NSString *text = self.inputField.stringValue;
        if (text.length > 0) {
            [self appendOutput:[NSString stringWithFormat:@"$ %@", text]];
            self.inputField.stringValue = @"";
            [self executeCommand:text];
        }
    }
}

- (void)runScript:(NSString *)path {
    std::ifstream file([path UTF8String]);
    if (!file.is_open()) {
        [self appendOutput:[NSString stringWithFormat:@"Ошибка: не удалось открыть скрипт %@", path]];
        return;
    }
    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line.rfind("//", 0) == 0) continue;
        [self appendOutput:[NSString stringWithFormat:@"$ %s", line.c_str()]];
        [self executeCommand:[NSString stringWithUTF8String:line.c_str()]];
    }
}

- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
    char user[128], host[128];
    getlogin_r(user, sizeof(user));
    gethostname(host, sizeof(host));
    NSString *title = [NSString stringWithFormat:@"Эмулятор [%s@%s]", user, host];

    NSRect frame = NSMakeRect(200, 200, 680, 460);
    self.window = [[NSWindow alloc] initWithContentRect:frame
        styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        backing:NSBackingStoreBuffered defer:NO];
    [self.window setTitle:title];

    NSView *content = self.window.contentView;

    NSScrollView *scroll = [[NSScrollView alloc] initWithFrame:NSMakeRect(10, 48, 660, 400)];
    scroll.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    scroll.hasVerticalScroller = YES;

    self.terminalView = [[NSTextView alloc] initWithFrame:scroll.bounds];
    self.terminalView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    self.terminalView.backgroundColor = [NSColor blackColor];
    self.terminalView.textColor = [NSColor greenColor];
    self.terminalView.font = [NSFont fontWithName:@"Menlo" size:13] ?: [NSFont monospacedSystemFontOfSize:13 weight:NSFontWeightRegular];
    self.terminalView.editable = NO;
    scroll.documentView = self.terminalView;
    [content addSubview:scroll];

    self.inputField = [[NSTextField alloc] initWithFrame:NSMakeRect(10, 10, 660, 28)];
    self.inputField.autoresizingMask = NSViewWidthSizable | NSViewMaxYMargin;
    self.inputField.backgroundColor = [NSColor colorWithWhite:0.15 alpha:1.0];
    self.inputField.textColor = [NSColor whiteColor];
    self.inputField.font = [NSFont fontWithName:@"Menlo" size:13] ?: [NSFont monospacedSystemFontOfSize:13 weight:NSFontWeightRegular];
    self.inputField.delegate = self;
    [content addSubview:self.inputField];

    [self.window makeKeyAndOrderFront:nil];
    [self.window makeFirstResponder:self.inputField];

    if (self.scriptPath && self.scriptPath.length > 0) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [self runScript:self.scriptPath];
        });
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}
@end

int main(int argc, char *argv[]) {
    std::string vfsPath, scriptPath;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--vfs" && i + 1 < argc) vfsPath = argv[++i];
        if (std::string(argv[i]) == "--script" && i + 1 < argc) scriptPath = argv[++i];
    }

    VirtualFileSystem vfs;
    vfs.loadFromZip(vfsPath);
    ShellEmulator shell(vfs);

    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        // ДВЕ НОВЫЕ СТРОКИ: делаем приложение полноценным (с фокусом клавиатуры)
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        
        EmulatorApp *delegate = [[EmulatorApp alloc] init];
        delegate.vfs = &vfs;
        delegate.shell = &shell;
        if (!scriptPath.empty()) {
            delegate.scriptPath = [NSString stringWithUTF8String:scriptPath.c_str()];
        }
        app.delegate = delegate;
        
        // ВЫВОДИМ НА ПЕРЕДНИЙ ПЛАН
        [app activateIgnoringOtherApps:YES];
        
        [app run];
    }
    return 0;
}