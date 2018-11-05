//Daemon
import std.stdio;
import std.conv;
import std.format;
import std.string;
import core.thread;
import std.algorithm;

class Led {
  string path;
  ulong length;
  ulong keypoint_count;
  Keypoint[] keypoints;
  this(string path, ulong[] rawdata) {
    this.path = path;
    this.length = rawdata[0];
    this.keypoint_count = rawdata[1];
  }

  auto addKeypoint(Keypoint point) {
    keypoints ~= point;
  }

  auto getPath() {
    return path;
  }

  auto getLength() {
    return length;
  }

  auto getBlend(double pos) {
    Keypoint last_keypoint;
    foreach(i; 0..keypoints.length) {
      if (keypoints[i] <= pos && pos <= keypoints[i+1]) {
        //Get the percentage mix between the two positions
        double mix = (pos-keypoints[i].getPos())/(keypoints[i+1].getPos()-keypoints[i].getPos());
        return keypoints[i].mix(keypoints[i+1], pos);
      }
    }
    //Otherwise mix the last and first point
    return keypoints[0].getRgb();
  }

  auto getBlendRounded(double pos) {
    auto blend = getBlend(pos);
    // I hate floating point
    return [clamp!(double)(blend[0],0.0,255.0),clamp!(double)(blend[1],0.0,255.0),clamp!(double)(blend[2],0.0,255.0)].to!(ubyte[]);
  }

  void toString(scope void delegate(const(char)[]) sink) const {
    foreach (keypoint; keypoints) {
      sink(keypoint.to!string);
    }
  }
}

auto rgbToHex(ubyte[] rgb) {
  return format!"%02X%02X%02X"(rgb[0],rgb[1],rgb[2]);
}

class Keypoint {
  double pos;
  ubyte r;
  ubyte g;
  ubyte b;
  this(double pos, ubyte[] rgb) {
    this.pos = pos;
    this.r = rgb[0];
    this.g = rgb[1];
    this.b = rgb[2];
  }

  auto getPos() {
    return pos;
  }

  auto getR() {
    return r;
  }
  auto getG() {
    return g;
  }
  auto getB() {
    return b;
  }

  auto mixR(Keypoint other, double mix) {
    return getR() * mix + other.getR() * (1 - mix);
  }
  auto mixG(Keypoint other, double mix) {
    return getG() * mix + other.getG() * (1 - mix);
  }
  auto mixB(Keypoint other, double mix) {
    return getB() * mix + other.getB() * (1 - mix);
  }

  auto mix(Keypoint other, double mix) {
    return [mixR(other,mix), mixG(other,mix), mixB(other,mix)];
  }

  double[] getRgb() {
    return [getR().to!double, getG().to!double, getB().to!double];
  }

  ubyte[] getRgbRounded() {
    return [getR(), getG(), getB()];
  }

  int opCmp(ref const Keypoint other) const {
    if (pos > other.pos) {
      return 1;
    } else if (pos < other.pos) {
      return -1;
    }
    return 0;
  }

  int opCmp(ref const double other) const {
    if (pos > other) {
      return 1;
    } else if (pos < other) {
      return -1;
    }
    return 0;
  }

  void toString(scope void delegate(const(char)[]) sink) const {
    auto posstr = pos.to!(string);
    sink("Keypoint<" ~ posstr ~ "("~this.r.to!(string)~","~this.g.to!(string)~","~this.b.to!(string)~")>");
  }
}

class LedBlenderThread : Thread {
  double resolution = 0.01;
  Led led;
  this(Led led) {
    this.led = led;
    super(&run);
  }

  auto run() {
    while (true) {
      auto speed = resolution/(led.getLength().to!double);
      for (double i = 0; i<1;i+=speed) {
        auto led_output = std.stdio.File(led.getPath(), "w");
        led_output.writeln(rgbToHex(led.getBlendRounded(i)));
        led_output.close();
        sleep(dur!("msecs")( (1000*resolution).to!long ));
      }
    }
  }
}

void main(string[] args) {
  File f;
  if (args.length == 2) {
    switch (args[1]) {
      case "-h":
        writeln("Usage: b76 [-h|file]");
        break;
      default:
        f = std.stdio.File(args[1]);
        break;
    }
  } else {
    f = std.stdio.File("/var/lib/b76/config.b76");
  }
  auto device = std.stdio.File("/sys/devices/virtual/dmi/id/product_version").readln().chop();
  switch (device) {
    case "oryp4":
    case "oryp2-ess":
    case "serw11":
      break;
    default:
      writeln("Error: This machine is unsupported.");
      return;
  }

  auto led_count = f.rawRead(new ubyte[1])[0];
  auto led_paths = [
    "/sys/class/leds/system76::kbd_backlight/color_left",
    "/sys/class/leds/system76::kbd_backlight/color_center",
    "/sys/class/leds/system76::kbd_backlight/color_right"
  ];

  Led[] leds;

  foreach (led_path; led_paths) {
    auto led_header = f.rawRead(new ulong[2]);
    leds ~= new Led(led_path, led_header);
  }

  foreach (led; leds) {
    foreach(keypoint_index; 0..led.keypoint_count) {
      auto pos = f.rawRead(new double[1])[0];
      auto rgb = f.rawRead(new ubyte[3]);
      led.addKeypoint(new Keypoint(pos, rgb));
    }
    (new LedBlenderThread(led)).start();
  }
}
