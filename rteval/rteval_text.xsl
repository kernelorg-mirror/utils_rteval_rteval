<?xml version="1.0"?>
<!-- SPDX-License-Identifier: GPL-2.0-or-later -->
<xsl:stylesheet  version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>

  <!--                       -->
  <!-- Main report framework -->
  <!--                       -->
  <xsl:template match="/rteval">
    <xsl:text>  ===================================================================&#10;</xsl:text>
    <xsl:text>   rteval (v</xsl:text><xsl:value-of select="@version"/><xsl:text>) report&#10;</xsl:text>
    <xsl:text>  -------------------------------------------------------------------&#10;</xsl:text>
    <xsl:text>   Test run:     </xsl:text>
    <xsl:value-of select="run_info/date"/><xsl:text> </xsl:text><xsl:value-of select="run_info/time"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Loads:        </xsl:text>
    <xsl:choose>
      <xsl:when test="loads">
        <xsl:value-of select="loads/@loads"/><xsl:text> loads run on cores </xsl:text><xsl:value-of select="loads/@loadcpus"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>none</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Measurement:  </xsl:text>
    <xsl:text>measurement threads run on cores </xsl:text><xsl:value-of select="Measurements/@measurecpus"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Run time:     </xsl:text>
    <xsl:value-of select="run_info/@days"/><xsl:text> days </xsl:text>
    <xsl:value-of select="run_info/@hours"/><xsl:text>h </xsl:text>
    <xsl:value-of select="run_info/@minutes"/><xsl:text>m </xsl:text>
    <xsl:value-of select="run_info/@seconds"/><xsl:text>s</xsl:text>
    <xsl:text>&#10;</xsl:text>
    <xsl:if test="run_info/annotate">
      <xsl:text>   Remarks:      </xsl:text>
      <xsl:value-of select="run_info/annotate"/>
    </xsl:if>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:text>   Tested node:  </xsl:text>
    <xsl:value-of select="SystemInfo/uname/node|uname/node"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Model:        </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='System Information']/Field[@Name='Manufacturer']"/>
    <xsl:text> - </xsl:text><xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='System Information']/Field[@Name='Product Name']"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   BIOS version: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='BIOS Information']/Field[@Name='Vendor']"/>
    <xsl:text> (ver: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='BIOS Information']/Field[@Name='Version']"/>
    <xsl:text>, rev: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='BIOS Information']/Field[@Name='BIOS Revision']"/>
    <xsl:text>, release date: </xsl:text>
    <xsl:value-of select="SystemInfo/DMIinfo/Handle[@name='BIOS Information']/Field[@Name='Release Date']"/>
    <xsl:text>)</xsl:text>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:text>   CPU cores:    </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/CPUtopology">
	<xsl:value-of select="SystemInfo/CPUtopology/@num_cpu_cores"/>
	<xsl:text> (online: </xsl:text>
	<xsl:value-of select="SystemInfo/CPUtopology/@num_cpu_cores_online"/>
    <xsl:if test="SystemInfo/CPUtopology/@num_cpu_cores_isolated != 0">
      <xsl:text>, isolated: </xsl:text>
      <xsl:value-of select="SystemInfo/CPUtopology/@num_cpu_cores_isolated"/>
    </xsl:if>
	<xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="hardware/cpu_topology">
        <xsl:value-of select="hardware/cpu_topology/@num_cpu_cores"/>
	<xsl:text> (online: </xsl:text>
	<xsl:value-of select="hardware/cpu_topology/@num_cpu_cores_online"/>
	<xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="hardware/cpu_cores">
	<xsl:value-of select="hardware/cpu_cores"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   NUMA Nodes:   </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/Memory/numa_nodes">
        <xsl:value-of select="SystemInfo/Memory/numa_nodes"/>
      </xsl:when>
      <xsl:when test="hardware/numa_nodes">
        <xsl:value-of select="hardware/numa_nodes"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Memory:       </xsl:text>
    <xsl:value-of select="SystemInfo/Memory/memory_size|hardware/memory_size"/>
    <xsl:choose>
      <xsl:when test="SystemInfo/Memory/memory_size/@unit">
	<xsl:value-of select="concat(' ',SystemInfo/Memory/memory_size/@unit)"/>
      </xsl:when>
      <xsl:when test="hardware/memory_size/@unit">
	<xsl:value-of select="concat(' ',hardware/memory_size/@unit)"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:text> kB</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Kernel:       </xsl:text>
    <xsl:value-of select="SystemInfo/uname/kernel|uname/kernel"/>
    <xsl:if test="SystemInfo/uname/kernel/@is_RT = '1' or uname/kernel/@is_RT = '1'">  (RT enabled)</xsl:if>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Base OS:      </xsl:text>
    <xsl:value-of select="SystemInfo/uname/baseos|uname/baseos"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="SystemInfo/ContainerInfo/container = 'true'">
      <xsl:text>   Container:    Running in a container&#10;</xsl:text>
    </xsl:if>

    <xsl:text>   Architecture: </xsl:text>
    <xsl:value-of select="SystemInfo/uname/arch|uname/arch"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Clocksource:  </xsl:text>
    <xsl:value-of select="SystemInfo/Kernel/ClockSource/source[@current='1']|clocksource/current"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Available:    </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/Kernel/ClockSource/source">
        <xsl:for-each select="SystemInfo/Kernel/ClockSource/source">
          <xsl:value-of select="."/>
          <xsl:text> </xsl:text>
        </xsl:for-each>
      </xsl:when>
      <xsl:when test="clocksource/available">
        <xsl:value-of select="clocksource/available"/>
      </xsl:when>
      <xsl:otherwise>(unknown)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>   Tuned state:  </xsl:text>
    <xsl:choose>
      <xsl:when test="SystemInfo/Tuned/@present='1'">
        <xsl:value-of select="SystemInfo/Tuned/active_profile"/>
        <xsl:text> profile</xsl:text>
          <xsl:if test="SystemInfo/Tuned/active_profile != 'unknown'">
            <xsl:text>, verification: </xsl:text>
            <xsl:value-of select="SystemInfo/Tuned/verified"/>
          </xsl:if>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>not present</xsl:text>
        </xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;&#10;</xsl:text>

    <!-- Display core sharing warnings if present -->
    <xsl:if test="SystemInfo/CPUtopology/CoreSharingWarnings/warning">
      <xsl:text>   Core Sharing Warnings:&#10;</xsl:text>
      <xsl:for-each select="SystemInfo/CPUtopology/CoreSharingWarnings/warning">
        <xsl:text>       </xsl:text>
        <xsl:value-of select="."/>
        <xsl:text>&#10;</xsl:text>
      </xsl:for-each>
      <xsl:text>&#10;</xsl:text>
    </xsl:if>

    <xsl:text>   System load:&#10;</xsl:text>
    <xsl:text>       Load average: </xsl:text>
    <xsl:value-of select="loads/@load_average"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="loads/command_line">
      <xsl:text>&#10;</xsl:text>
      <xsl:text>       Executed loads:&#10;</xsl:text>
      <xsl:apply-templates select="loads/command_line"/>
    </xsl:if>
    <xsl:text>&#10;</xsl:text>

    <xsl:text> Cmdline:        </xsl:text>
    <xsl:value-of select="SystemInfo/cmdlineInfo/cmdline"/>
    <xsl:text>&#10;</xsl:text>

    <!-- Generate a summary report for all measurement modules -->
    <xsl:apply-templates select="Measurements"/>
   <xsl:text>  ===================================================================&#10;</xsl:text>
</xsl:template>
  <!--                              -->
  <!-- End of main report framework -->
  <!--                              -->


  <!--  Formats and lists all used commands lines  -->
  <xsl:template match="command_line">
    <xsl:text>         - </xsl:text>
    <xsl:value-of select="@name"/>
    <xsl:text>: </xsl:text>
    <xsl:choose>
      <xsl:when test="not(@run) or @run = '1'">
	<xsl:value-of select="."/>
      </xsl:when>
      <xsl:otherwise>(Not run)</xsl:otherwise>
    </xsl:choose>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <xsl:template match="/rteval/Measurements">
    <xsl:text>   Measurements: </xsl:text>
    <xsl:text>&#10;</xsl:text>

    <!-- Format other sections of the report, if they are found                 -->
    <!-- To add support for even more sections, just add them into the existing -->
    <!-- xsl:apply-tempaltes tag, separated with pipe(|)                        -->
    <!--                                                                        -->
    <!--       select="cyclictest|new_foo_section|another_section"              -->
    <!--                                                                        -->
    <xsl:apply-templates select="cyclictest|timerlat|hwlatdetect[@format='1.0']|sysstat"/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- Format the cyclictest section of the report -->
  <xsl:template match="/rteval/Measurements/cyclictest">
    <xsl:text>       Latency test&#10;</xsl:text>

    <xsl:text>          Started: </xsl:text>
    <xsl:value-of select="timestamps/runloop_start"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Stopped: </xsl:text>
    <xsl:value-of select="timestamps/runloop_stop"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Command: </xsl:text>
    <xsl:value-of select="@command_line"/>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:apply-templates select="abort_report"/>

    <xsl:text>          System:  </xsl:text>
    <xsl:value-of select="system/@description"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Statistics: &#10;</xsl:text>
    <xsl:apply-templates select="system/statistics"/>

    <!-- Add CPU core info and stats-->
    <xsl:apply-templates select="core">
      <xsl:sort select="@id" data-type="number"/>
    </xsl:apply-templates>
  </xsl:template>


  <!--  Format the CPU core section in the cyclictest part -->
  <xsl:template match="/rteval/Measurements/cyclictest/core">
    <xsl:text>          CPU core </xsl:text>
    <xsl:value-of select="@id"/>
    <xsl:text>       Priority: </xsl:text>
    <xsl:value-of select="@priority"/>
    <xsl:text>&#10;</xsl:text>
    <xsl:text>          Statistics: </xsl:text>
    <xsl:text>&#10;</xsl:text>
    <xsl:apply-templates select="statistics"/>
  </xsl:template>


  <!-- Generic formatting of statistics information -->
  <xsl:template match="/rteval/Measurements/cyclictest/*/statistics">
    <xsl:text>            Samples:           </xsl:text>
    <xsl:value-of select="samples"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="samples > 0">
      <xsl:text>            Mean:              </xsl:text>
      <xsl:value-of select="mean"/>
      <xsl:value-of select="mean/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Median:            </xsl:text>
      <xsl:value-of select="median"/>
      <xsl:value-of select="median/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mode:              </xsl:text>
      <xsl:value-of select="mode"/>
      <xsl:value-of select="mode/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Range:             </xsl:text>
      <xsl:value-of select="range"/>
      <xsl:value-of select="range/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Min:               </xsl:text>
      <xsl:value-of select="minimum"/>
      <xsl:value-of select="minimum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Max:               </xsl:text>
      <xsl:value-of select="maximum"/>
      <xsl:value-of select="maximum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mean Absolute Dev: </xsl:text>
      <xsl:value-of select="mean_absolute_deviation"/>
      <xsl:value-of select="mean_absolute_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Std.dev:           </xsl:text>
      <xsl:value-of select="standard_deviation"/>
      <xsl:value-of select="standard_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>
    </xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- Format the timerlat section of the report -->
  <xsl:template match="/rteval/Measurements/timerlat">
    <xsl:text>       Latency test&#10;</xsl:text>

    <xsl:text>          Started: </xsl:text>
    <xsl:value-of select="timestamps/runloop_start"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Stopped: </xsl:text>
    <xsl:value-of select="timestamps/runloop_stop"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Command: </xsl:text>
    <xsl:value-of select="@command_line"/>
    <xsl:text>&#10;&#10;</xsl:text>

    <xsl:if test="stoptrace_invoked">
     <xsl:text>rtla timerlat hit stop tracing</xsl:text>
     <xsl:text>
</xsl:text>
    <xsl:apply-templates select="stoptrace_report"/>
    <xsl:apply-templates select="max_timerlat_report"/>
    </xsl:if>

    <!-- Make sure the description is available before printing System: -->
    <xsl:if test="system/@description">
    <xsl:text>          System:  </xsl:text>
    <xsl:value-of select="system/@description"/>
    <xsl:text>&#10;</xsl:text>
    </xsl:if>

    <!-- If stoptrace_invoked is true, no Statistics are available -->
    <xsl:if test="stoptrace_invoked != 'true'">
    <xsl:text>          Statistics: &#10;</xsl:text>
    <xsl:apply-templates select="system/statistics"/>
    </xsl:if>

    <!-- Add CPU core info and stats-->
    <xsl:apply-templates select="core">
      <xsl:sort select="@id" data-type="number"/>
    </xsl:apply-templates>
  </xsl:template>


  <!--  Format the CPU core section in the timerlat part -->
  <xsl:template match="/rteval/Measurements/timerlat/core">
    <xsl:text>          CPU core </xsl:text>
    <xsl:value-of select="@id"/>
    <xsl:text>       Priority: </xsl:text>
    <xsl:value-of select="@priority"/>
    <xsl:text>&#10;</xsl:text>
    <xsl:text>          Statistics: </xsl:text>
    <xsl:text>&#10;</xsl:text>
    <xsl:apply-templates select="statistics"/>
  </xsl:template>


  <!-- Generic formatting of statistics information -->
  <xsl:template match="/rteval/Measurements/timerlat/*/statistics">
    <xsl:text>            Samples:           </xsl:text>
    <xsl:value-of select="samples"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:if test="samples > 0">
      <xsl:text>            Mean:              </xsl:text>
      <xsl:value-of select="mean"/>
      <xsl:value-of select="mean/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Median:            </xsl:text>
      <xsl:value-of select="median"/>
      <xsl:value-of select="median/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mode:              </xsl:text>
      <xsl:value-of select="mode"/>
      <xsl:value-of select="mode/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Range:             </xsl:text>
      <xsl:value-of select="range"/>
      <xsl:value-of select="range/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Min:               </xsl:text>
      <xsl:value-of select="minimum"/>
      <xsl:value-of select="minimum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Max:               </xsl:text>
      <xsl:value-of select="maximum"/>
      <xsl:value-of select="maximum/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Mean Absolute Dev: </xsl:text>
      <xsl:value-of select="mean_absolute_deviation"/>
      <xsl:value-of select="mean_absolute_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:text>            Std.dev:           </xsl:text>
      <xsl:value-of select="standard_deviation"/>
      <xsl:value-of select="standard_deviation/@unit"/>
      <xsl:text>&#10;</xsl:text>
    </xsl:if>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>


  <!-- Format the hwlatdetect test section of the report -->
  <xsl:template match="/rteval/Measurements/hwlatdetect[@format='1.0' and not(@aborted)]">
    <xsl:text>     Hardware latency detector&#10;</xsl:text>

    <xsl:text>       Run duration: </xsl:text>
    <xsl:value-of select="RunParams/@duration"/>
    <xsl:text> seconds&#10;</xsl:text>

    <xsl:text>       Threshold:    </xsl:text>
    <xsl:value-of select="RunParams/@threshold"/>
    <xsl:text>us&#10;</xsl:text>

    <xsl:text>       Width:       </xsl:text>
    <xsl:value-of select="RunParams/@width"/>
    <xsl:text>us&#10;</xsl:text>

    <xsl:text>       Window size: </xsl:text>
    <xsl:value-of select="RunParams/@window"/>
    <xsl:text>us&#10;&#10;</xsl:text>

    <xsl:text>       Threshold exceeded </xsl:text>
    <xsl:value-of select="samples/@count"/>
    <xsl:text> times&#10;</xsl:text>
    <xsl:apply-templates select="samples/sample"/>
  </xsl:template>

  <xsl:template match="/rteval/Measurements/hwlatdetect[@format='1.0' and @aborted > 0]">
    <xsl:text>     Hardware latency detector&#10;</xsl:text>
    <xsl:text>        ** WARNING ** hwlatedect failed to run&#10;</xsl:text>
  </xsl:template>

  <xsl:template match="/rteval/Measurements/hwlatdetect[@format='1.0']/samples/sample">
    <xsl:text>         - @</xsl:text>
    <xsl:value-of select="@timestamp"/>
    <xsl:text>  </xsl:text>
    <xsl:value-of select="@duration"/>
    <xsl:text>us&#10;</xsl:text>
  </xsl:template>

  <!-- Format the cyclictest section of the report -->
  <xsl:template match="/rteval/Measurements/sysstat">
    <xsl:text>       sysstat measurements&#10;</xsl:text>

    <xsl:text>          Started: </xsl:text>
    <xsl:value-of select="timestamps/runloop_start"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Stopped: </xsl:text>
    <xsl:value-of select="timestamps/runloop_stop"/>
    <xsl:text>&#10;</xsl:text>

    <xsl:text>          Records saved: </xsl:text>
    <xsl:value-of select="@num_entries"/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <!-- Format information about aborts - if present -->
  <xsl:template match="abort_report">
      <xsl:text>      Run aborted: </xsl:text>
      <xsl:value-of select="@reason"/>
      <xsl:text>&#10;</xsl:text>

      <xsl:if test="breaktrace">
        <xsl:text>                   </xsl:text>
        <xsl:text>Aborted due to latency exceeding </xsl:text>
        <xsl:value-of select="breaktrace/@latency_threshold"/>
        <xsl:text>us.&#10;</xsl:text>
        <xsl:text>                   </xsl:text>
        <xsl:text>Measured latency when stopping was </xsl:text>
        <xsl:value-of select="breaktrace/@measured_latency"/>
        <xsl:text>us.&#10;&#10;</xsl:text>
      </xsl:if>
  </xsl:template>

  <!-- Format posttrace information if present -->
  <xsl:template match="stoptrace_report">
     <xsl:text>## CPU </xsl:text>
     <xsl:value-of select="@CPU"/>
     <xsl:text> hit stop tracing, analyzing it ##</xsl:text>
     <xsl:text>
</xsl:text>


     <xsl:if test="Previous_IRQ_interference">
     <xsl:text>Previous IRQ interference:			 up to       </xsl:text>
     <xsl:value-of select="Previous_IRQ_interference"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Previous_IRQ_interference/@unit"/>
     <xsl:text>
</xsl:text>
     </xsl:if>

     <xsl:if test="IRQ_handler_delay">
     <xsl:text>IRQ handler delay:		                	</xsl:text>
     <xsl:value-of select="IRQ_handler_delay/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_handler_delay/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="IRQ_handler_delay/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_handler_delay/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>
     </xsl:if>

     <xsl:if test="IRQ_handler_delay_exit_from_idle">
     <xsl:text>IRQ handler delay:		(exit from idle)	</xsl:text>
     <xsl:value-of select="IRQ_handler_delay_exit_from_idle/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_handler_delay_exit_from_idle/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="IRQ_handler_delay_exit_from_idle/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_handler_delay_exit_from_idle/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>
     </xsl:if>

     <xsl:text>IRQ latency:</xsl:text>
     <xsl:text>						</xsl:text>
     <xsl:value-of select="IRQ_latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_latency/@unit"/>
     <xsl:text>
</xsl:text>

     <xsl:text>Timerlat IRQ duration:</xsl:text>
     <xsl:text>					</xsl:text>
     <xsl:value-of select="Timerlat_IRQ_duration/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Timerlat_IRQ_duration/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="Timerlat_IRQ_duration/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Timerlat_IRQ_duration/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>

     <xsl:if test="Blocking_thread">
     <xsl:text>Blocking thread:</xsl:text>
     <xsl:text>					</xsl:text>
     <xsl:value-of select="Blocking_thread/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Blocking_thread/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="Blocking_thread/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Blocking_thread/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>
     </xsl:if>

     <xsl:for-each select="blocking_thread">
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="name"/>
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="latency"/>
             <xsl:text> </xsl:text>
	     <xsl:value-of select="latency/@unit"/>
             <xsl:text>
</xsl:text>
     </xsl:for-each>

     <xsl:if test="Softirq_interference">
     <xsl:text>Softirq interference:</xsl:text>
     <xsl:text>					</xsl:text>
     <xsl:value-of select="Softirq_interference/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Softirq_interference/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="Softirq_interference/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Softirq_interference/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>
     </xsl:if>

     <xsl:for-each select="softirq_interference">
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="name"/>
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="latency"/>
             <xsl:text> </xsl:text>
	     <xsl:value-of select="latency/@unit"/>
             <xsl:text>
</xsl:text>
     </xsl:for-each>

     <xsl:if test="IRQ_interference">
     <xsl:text>IRQ interference:</xsl:text>
     <xsl:text>					</xsl:text>
     <xsl:value-of select="IRQ_interference/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_interference/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="IRQ_interference/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="IRQ_interference/latency_percent/@unit"/>
     <xsl:text>)
</xsl:text>
     </xsl:if>

     <xsl:for-each select="irq_interference">
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="name"/>
	     <xsl:text>			</xsl:text>
	     <xsl:value-of select="latency"/>
             <xsl:text> </xsl:text>
	     <xsl:value-of select="latency/@unit"/>
             <xsl:text>
</xsl:text>
     </xsl:for-each>

     <xsl:text>--------------------------------------------------------------------------------</xsl:text>
     <xsl:text>Thread latency:</xsl:text>
     <xsl:text>						</xsl:text>
     <xsl:value-of select="Thread_latency/latency"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Thread_latency/latency/@unit"/>
     <xsl:text> (</xsl:text>
     <xsl:value-of select="Thread_latency/latency_percent"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Thread_latency/latency_percent/@unit"/>
     <xsl:text>)

</xsl:text>
  </xsl:template>

  <xsl:template match="max_timerlat_report">
     <xsl:text>
</xsl:text>
     <xsl:text>Max timerlat IRQ latency from idle:</xsl:text>
     <xsl:value-of select="Max_timerlat_IRQ_latency_from_idle"/>
     <xsl:text> </xsl:text>
     <xsl:value-of select="Max_timerlat_IRQ_latency_from_idle/@unit"/>
     <xsl:text> in cpu </xsl:text>
     <xsl:value-of select="@CPU"/>
     <xsl:text>
</xsl:text>
  </xsl:template>

</xsl:stylesheet>
