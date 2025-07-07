using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.SignalR;
using Microsoft.CognitiveServices.Speech;
using Microsoft.CognitiveServices.Speech.Audio;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSignalR();

var app = builder.Build();
app.MapHub<AudioHub>("/audiohub");
app.Run();

public class AudioHub : Hub
{
    private static SpeechRecognizer _recognizer;
    private static PushAudioInputStream _pushStream;

    public override async Task OnConnectedAsync()
    {
        var config = SpeechConfig.FromSubscription("YOUR_AZURE_KEY", "YOUR_REGION");
        config.SpeechRecognitionLanguage = "en-US";

        _pushStream = AudioInputStream.CreatePushStream(AudioStreamFormat.GetWaveFormatPCM(16000, 16, 1));
        var audioConfig = AudioConfig.FromStreamInput(_pushStream);
        _recognizer = new SpeechRecognizer(config, audioConfig);

        _recognizer.Recognized += async (s, e) =>
        {
            if (e.Result.Reason == ResultReason.RecognizedSpeech)
            {
                var text = e.Result.Text;
                Console.WriteLine($"Recognized: {text}");

                if (text.ToLower().Contains("recommend a dress"))
                {
                    var recommendation = "For your job interview tomorrow, wear a formal business suit or a conservative dress.";
                    await Clients.Caller.SendAsync("transcript", recommendation);
                }
                else
                {
                    await Clients.Caller.SendAsync("transcript", text);
                }
            }
        };

        await _recognizer.StartContinuousRecognitionAsync();
        await base.OnConnectedAsync();
    }

    public async Task AudioStream(byte[] chunk)
    {
        _pushStream.Write(chunk);
    }

    public override async Task OnDisconnectedAsync(Exception exception)
    {
        await _recognizer.StopContinuousRecognitionAsync();
        _pushStream.Close();
        await base.OnDisconnectedAsync(exception);
    }
}
